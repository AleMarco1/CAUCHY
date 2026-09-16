# -*- coding: utf-8 -*-
"""
paper2_patch_chiusura_fase5.py -- chiude la Fase 5 nei due documenti indice:
checklist_paper2.md (rev. 3.20 -> 3.21) e paper2_stato.md (quinta -> sesta revisione).

DUE FILE, un solo comando. Si valida TUTTO prima di scrivere: se le ancore di uno non tornano,
nessuno dei due viene toccato e non nasce nessun backup. Il verify controlla entrambi.

checklist_paper2.md (otto modifiche):
  C1  intestazione: rev. 3.20 -> 3.21, record 60, Fase 5 chiusa
  C2  base documentale: M26 R1 "sottomessa 23 ago" -> pubblicato il 9 set 2026
  C3  voce 5.1: "denominatori conservativi ovunque" -> dichiarati termine per termine
  C4  voce 5.2: due righe -> quattro, e chiusa da P1-13
  C5  voce 5.3: da [~] a [x], con il rimando all'esito di Fase 4
  C6  voce 5.4: cinque/sei practice per M26 -> sette, sezione del Paper 2
  C7  voci 5.5 e 5.6: da una smentita a 12/1/5 classificate; 5.6 decisa
  C8  Fase 6: nuovo punto 6.8 -- D6 e il residuo 3, rinviati con il loro motivo

paper2_stato.md (cinque modifiche):
  S1  intestazione: 11 set, quinta revisione -> 12 set, sesta
  S2  nuovo blocco "Cosa e' cambiato nella sesta revisione", prima del quinto
  S3  "Stato in una riga": riga nuova con i valori del 12 settembre
  S4  sezione 3: "55 record" -> "60 record", con i cinque della Fase 5
  S5  Aperti: Z-P1 da nove voci a tredici, e Z-checklist alla rev. 3.21

Uso:
  python paper2_patch_chiusura_fase5.py selftest
  python paper2_patch_chiusura_fase5.py dry-run --checklist <p>/checklist_paper2.md --stato <p>/paper2_stato.md
  python paper2_patch_chiusura_fase5.py apply   --checklist ... --stato ...
  python paper2_patch_chiusura_fase5.py verify  --checklist ... --stato ...

Stesse garanzie degli altri patcher: ancore uniche, rifiuto se gia' applicata, BOM e fine riga
preservati per file, inversa = originale byte per byte, scrittura atomica con backup, verify sul
file riletto dal disco.
"""
import argparse
import datetime as _dt
import hashlib
import os
import sys
import tempfile

# ---------------------------------------------------------------------------
# Testi -- checklist_paper2.md
# ---------------------------------------------------------------------------

C1_OLD = ("### rev. 3.20 — 11 settembre 2026 — record 57-59; "
          "**LA FASE 4 È DECISA: sei regole su sei falliscono**")
C1_NEW = ("### rev. 3.21 — 12 settembre 2026 — record 60; **LA FASE 5 È CHIUSA: ogni denominatore "
          "dichiarato, quattro correzioni al Paper 1, un residuo rinviato alla Fase 6**")

C2_OLD = "> **Base documentale.** M26 R1 (`MN-26-2100-P.R1`, sottomessa 23 ago 2026), Paper 1"
C2_NEW = ("> **Base documentale.** M26 (`MN-26-2100-P`, **accettata il 9 set 2026 e pubblicata**; "
          "ricevuta in forma rivista il 23 ago), Paper 1")

C3_OLD = ("- [ ] **5.1** Budget sistematico aggiornato: banda 17–29% del Paper 1, termine AP misurato, ±3.4%\n"
          "      residuo di maschera, termine di tiling. Denominatori conservativi ovunque.")
C3_NEW = (
    "- [x] **5.1 — FATTO il 12 set, in `papers/paper2/paper2_budget_5_1.md`.** Undici termini, ognuno\n"
    "      con **tre dichiarazioni**: denominatore statistico (SEM appaiata / dispersione per\n"
    "      realizzazione / nessuno), base della percentuale (% di *D* o % di *N*_H1, mai «%» da solo)\n"
    "      e forma (misura Δ ± σ / limite \\|Δ\\| + 3σ / sottrazione / banda).\n"
    "      **«Denominatori conservativi ovunque» è ritirato**, e con una ragione: per un limite un σ\n"
    "      più largo è prudente, per una misura la quadratura al posto della SEM appaiata sottostima\n"
    "      l'effetto. La parola dice cose opposte nei due casi.\n"
    "      **Due colonne che non si mescolano:** A ciò che sposta la media o il lato dati, B ciò che\n"
    "      tocca la dispersione per realizzazione — il fattore 1.44 del tiling è B.\n"
    "      **R3-bis, eccezione dichiarata:** un termine misurato su un campione di *geometrie* e\n"
    "      trasferito a una geometria nuova porta la **dispersione fra le geometrie provate**. Vale\n"
    "      per la sola riga 9.\n"
    "      **La banda non è 17–29 %, è 17.3–31.2 %** (SGC *k*=3 sui 2000; P25 di SGC da P1-8).\n"
    "      **Il ±3.4 % non è quello che sembrava:** è la media del bias in punti percentuali di un\n"
    "      contrasto del 23.9 %, non una dispersione. La riga 9 porta ora −14.3 % ± **11.9 %**\n"
    "      relativo, cioè ±2.4 pp sul 20.3 — voce **P1-12** del Paper 1.\n"
    "      **Aperti di 5.1:** la nota 1 (le % dell'AP vanno su ⟨*N*⟩_mock a *k*=1, letto dal ramo\n"
    "      unitario, non ricostruito dal 25.46 % arrotondato) e i file sorgente di tre valori."
)

C4_OLD = ("- [ ] **★ 5.2 — Tab. 8 del Paper 1, due righe.** *\"fiducial cosmology / AP\"* → bound numerico;\n"
          "      *\"box tiling\"* → superata da M26 R1 §5.6, citare i numeri e non lo stato \"open\".")
C4_NEW = (
    "- [x] **★ 5.2 — FATTO il 12 set: sono QUATTRO righe, non due.** Voce **P1-13** di\n"
    "      `modifiche_paper1.md`.\n"
    "      1. *fiducial cosmology / AP* → nella forma **(B)**: la falsificazione senza i numeri non\n"
    "         pubblicati della Fase 3. «Il *F* che azzererebbe il deficit sta 67–265× fuori da\n"
    "         \\|*F*−1\\| ≤ 0.027», stato «falsified as sole cause; amplitude in preparation»;\n"
    "      2. *box tiling* → da «unquantified, open» a «< 73 generatori (1.0 % di *D*) a 3σ, bounded»;\n"
    "      3. *snapshot* → «∼13 (0.2 %)» è il valore centrale di −53 ± 112, cioè di un nullo: diventa\n"
    "         «< 97 (1.4 %) a 3σ su Δ*z* ≈ 0.25»;\n"
    "      4. *unit-weight rebuild of DESI* → il «∼1 %» è di *N*; sul deficit vale il **4.3 %**, e\n"
    "         questa diventa **la prima riga della tabella sopra il 2 %**: «sub-dominant» non è più la\n"
    "         parola giusta.\n"
    "      La quinta riga, *mock voxelisation weighting*, la aggiorna **P1-9**: le due voci vanno\n"
    "      applicate insieme."
)

C5_OLD = "- [~] **✦✧ 5.3 — Stabilità del residuo beyond-two-point. CANCELLO COSTRUITO E SUPERATO**,"
C5_NEW = ("- [x] **✦✧ 5.3 — CHIUSO.** *(La verifica su v2 non è più in attesa: la Fase 4 è decisa e\n"
          "      l'ensemble di riferimento resta v1 — record 59, 60.)* **CANCELLO COSTRUITO E SUPERATO**,")

C6_OLD = "- [ ] **✦ 5.4 — CINQUE \"practice\" per §6.2 di M26**, non tre:"
C6_NEW = ("- [x] **✦ 5.4 — FATTO il 12 set: SETTE practice, e non vanno in M26.** Il §6.2 di M26 è\n"
          "      **pubblicato e chiuso** con tre practice, quindi le nostre diventano una **sezione del\n"
          "      Paper 2** che lo cita e lo estende: su questo punto M26 non dice nulla di falso, dice\n"
          "      meno. Testo in `papers/paper2/paper2_5_4_practice.md`.\n"
          "      **La practice 2 ha cambiato argomento.** Era «pesare i mock toglie le punte di δ», e\n"
          "      la Fase 4 lo ha **smentito** (è l'esito di P1-11): ora poggia sull'appaiamento\n"
          "      like-for-like e sull'ampiezza misurata (1.24 % di *D* in NGC), **e deve dichiarare che\n"
          "      l'effetto atteso non c'è** — altrimenti chi la seguisse per quel motivo troverebbe il\n"
          "      contrario.\n"
          "      **La practice 6 ha il suo numero**, e la prima stesura della chiusura sbagliava a dire\n"
          "      che serviva un run: `d5c_n_clipped` compare **18 195 volte** nei registri di Fase 3, il\n"
          "      fiduciale incluso — 1.00 per realizzazione in NGC, 0.345 in SGC, massimo 13, cioè una o\n"
          "      due galassie su ~5×10⁵. `clipped_rand` è **0 in tutti e 14** i record di Fase 2 e il run\n"
          "      in spazio reale ha **200 zeri su 200**: escono solo le galassie, ed è la RSD a\n"
          "      spingerle fuori. *(Resta fuori `n_clip_inmask`, che la sonda D5c calcola e il registro\n"
          "      non archivia.)*\n"
          "      **SETTIMA PRACTICE, dal record di riga 35:** ogni flag di run deve entrare nel\n"
          "      **calcolo**, non solo nel record — `--real-space` entrava nel record e nella chiave di\n"
          "      ripresa ma non nel conto, e 2400 celle sono uscite identiche intero per intero al run\n"
          "      in spazio redshift. È un difetto di pipeline, non una predizione smentita.\n"
          "      *(Testo originale della voce, che resta come storia:)* **CINQUE \"practice\" per §6.2 di M26**, non tre:")

C7_OLD = ("- [ ] **✦ 5.5 — Una predizione dichiarata e smentita, da riportare nel manoscritto.** «σ(realizzazione)\n"
          "      domina, oltre l'80%» è stata smentita di **due ordini di grandezza**; la decomposizione le\n"
          "      assegna il 13.4%. Più la P1 di D3. Il Paper 1 ha già stabilito il precedente riportando il\n"
          "      fallimento dell'albero decisionale pre-registrato.\n"
          "- [ ] **5.6** Se 4.3b lo richiede, nuova nota correttiva — sempre unica, mai a pezzi.")
C7_NEW = (
    "- [x] **✦ 5.5 — FATTO il 12 set: NON è una predizione, sono DICIOTTO voci classificate.** Il\n"
    "      conto veniva da questa checklist, non dal registro: dei 59 record, **26** portano insieme\n"
    "      una predizione dichiarata e il suo riscontro. Classificazione in\n"
    "      `papers/paper2/paper2_5_5_smentite.md`, letta record per record con `paper2_estrai.py`.\n"
    "      - **gruppo A, dodici voci** — dichiarate prima del run, undici cadute sul dato e **una che\n"
    "        regge** (il termine (c) non dipende dal punto, record 39: resta nella sezione, perché una\n"
    "        sezione di soli fallimenti è selezionata quanto una di soli successi). Due non erano in\n"
    "        nessuna lista: il clipping predetto sul residuo **anisotropo** (falsificato **senza\n"
    "        eseguire nulla**, da record già su disco) e le **due** predizioni distinte del record 16,\n"
    "        cadute in record diversi;\n"
    "      - **gruppo A-bis, una voce** — la maschera d'intersezione del record 24: esito **PARZIALE**,\n"
    "        0.4962 e 0.4741 contro una soglia a 2/3. Sotto soglia, quindi non smentita; non\n"
    "        abbastanza per una conferma. Ha un gruppo suo perché l'esito che non risolve è il più\n"
    "        facile da far sparire in uno dei due gruppi pieni;\n"
    "      - **gruppo B, cinque voci** — soglie o caratterizzazioni mal poste, dove la conclusione non\n"
    "        cambia. La più scomoda: la **P1 di D3 è ritirata *come falsificazione*** (0.22σ dalla sua\n"
    "        soglia, errore standard 0.0224), e con essa il record 43, che aveva celebrato la\n"
    "        riproduzione di un attraversamento di soglia **senza potere**. Il rilievo è del referee,\n"
    "        non nostro, e va raccontato così.\n"
    "      **I 33 record esclusi sono stati controllati uno per uno:** undici sono le *metà\n"
    "      dichiarative* di predizioni il cui esito è già in A (15→19, 16→37 e 38, 30→31, 51→59), gli\n"
    "      altri dichiarano disegno, definizioni o rettifiche senza clausola di falsificazione.\n"
    "      **Nessuna smentita è sfuggita.** Il precedente del Paper 1 (l'albero decisionale\n"
    "      pre-registrato) si cita come pratica della serie, non come novità.\n"
    "- [x] **5.6 — DECISA il 12 set, prima di ogni scrittura di Fase 5: la nota serve, e va sul\n"
    "      Paper 1, non su M26.** Criterio: una nota serve se un esito di Fase 4 rende **falsa**\n"
    "      un'affermazione — un numero fuori dalla sua incertezza, un segno, un'attribuzione causale;\n"
    "      ciò che la Fase 4 aggiunge senza contraddire va nel Paper 2.\n"
    "      **Paper 1:** il §8.1, la didascalia della Tab. 9 e il §10 (vii) attribuiscono il massimo a\n"
    "      *k*=1 ai voxel «FKP-contaminated». 4.3b lo smentisce (record 59) e il §7.2 si contraddiceva\n"
    "      già da solo — quei voxel «carry essentially no cycles». È la voce **P1-10**, unica e non a\n"
    "      pezzi; nella stessa tornata entrano **P1-11**, **P1-12** e **P1-13**.\n"
    "      **M26: nessuna nota.** Non riporta *D*(*k*) per livello e non attribuisce il massimo; il\n"
    "      §4.1 attribuisce i picchi di δ alla copertura quasi nulla, cioè alla lettura che la Fase 4\n"
    "      conferma. La riga −78.0 ± 8.0 della Tab. 1 contro −89.15 ± 1.25 sta a 1.4σ e vale l'1.24 %\n"
    "      del deficit, dentro il «1–2 %» dichiarato.\n"
    "      **M26 è pubblicato: nessun erratum**, e non perché nulla sia falso — tre delle quattro voci\n"
    "      della ricognizione lo sono — ma perché **nessun errore è consequenziale**: deficit, rango,\n"
    "      esclusione di *w*₀CDM e significatività restano. Le quattro voci (il +309 dato come 1–2 %\n"
    "      del deficit quando ne vale il 4.30 %; lo snapshot citato col valore centrale di un nullo; il\n"
    "      rimando del §2 alla «Section 5.4», che non ne parla; e il «14 %» del §4.1, che è 13.3)\n"
    "      restano registrate in `modifiche_paper1.md`. Il punto si riapre solo se una tocca una\n"
    "      conclusione. **P1-13 corregge comunque il +309 e lo snapshot nella Tab. 8 del Paper 1**,\n"
    "      così chi legge la serie trova i numeri giusti."
)

C8_OLD = ("- [ ] **✧✧✧✧✧ 6.7 — `REPRODUCIBILITY.md` alla radice** (ex R2 di `paper2_stato.md`): mappa\n"
          "      manoscritto → tag → version DOI → digest congelati. Era bloccato da P-A1, che è chiuso: il tier\n"
          "      `records` è passato a 224 file e `5364cf2e…`, e l'emendamento 11 lo registra. Scrivibile adesso.")
C8_NEW = C8_OLD + "\n" + (
    "- [ ] **✦✦ 6.8 — D6 e il terzo residuo di Fase 4, RINVIATI QUI con il loro motivo** *(12 set,\n"
    "      record 60; stessa forma con cui la Fase 2 rimandava ciò che non poteva chiudere)*.\n"
    "      **Che cosa è in sospeso:** il **62.7 %** (NGC) e **60.3 %** (SGC) di varianza cosmologica\n"
    "      che i sette parametri non spiegano (D5), che dovrebbe collegarsi al residuo\n"
    "      beyond-two-point di 1710 generatori del Paper 1 — e sarebbe il risultato più interessante\n"
    "      del paper.\n"
    "      **Perché non è collocabile adesso:** D6 è aperto con la sua riserva già dichiarata — la\n"
    "      sequenza di modelli **non converge** (il 48.3 % è un limite superiore, non una misura) e la\n"
    "      **provenienza di `pk_matrix` non è stabilita**, quindi i test B e C non sono interpretabili.\n"
    "      Senza D6 le due letture non si separano: se *P*(*k*) chiude il divario, *N*_H1 **è** una\n"
    "      statistica del due punti e i sette parametri fallivano solo perché la mappa\n"
    "      parametri → *P*(*k*) non è lineare; se non lo chiude, la parte non spiegata è **oltre il due\n"
    "      punti**.\n"
    "      **Nel frattempo:** il residuo **non entra** nel budget di 5.1 come termine — non è uno\n"
    "      spostamento della media (colonna A) né un fattore sulla dispersione (colonna B), è varianza\n"
    "      non attribuita, una terza cosa — e **non entra** nella discussione come risultato.\n"
    "      **Il tetto da non sbagliare due volte:** per predittori misurati sulla stessa realizzazione\n"
    "      non è 0.698 ma **0.832**.\n"
    "      **Da fare qui, in quest'ordine:** stabilire la provenienza di `pk_matrix`; far convergere la\n"
    "      sequenza di modelli; poi decidere quale delle due letture è sostenuta."
)

EDITS_CHK = [
    ("C1_intestazione", C1_OLD, C1_NEW),
    ("C2_base_documentale", C2_OLD, C2_NEW),
    ("C3_voce_5_1", C3_OLD, C3_NEW),
    ("C4_voce_5_2", C4_OLD, C4_NEW),
    ("C5_voce_5_3", C5_OLD, C5_NEW),
    ("C6_voce_5_4", C6_OLD, C6_NEW),
    ("C7_voci_5_5_e_5_6", C7_OLD, C7_NEW),
    ("C8_fase6_punto_6_8", C8_OLD, C8_NEW),
]

MARKERS_CHK = [
    "### rev. 3.21 — 12 settembre 2026 — record 60;",
    "**accettata il 9 set 2026 e pubblicata**",
    "- [x] **5.1 — FATTO il 12 set,",
    "- [x] **★ 5.2 — FATTO il 12 set: sono QUATTRO righe, non due.**",
    "- [x] **✦✧ 5.3 — CHIUSO.**",
    "- [x] **✦ 5.4 — FATTO il 12 set: SETTE practice, e non vanno in M26.**",
    "- [x] **✦ 5.5 — FATTO il 12 set: NON è una predizione, sono DICIOTTO voci classificate.**",
    "- [x] **5.6 — DECISA il 12 set,",
    "- [ ] **✦✦ 6.8 — D6 e il terzo residuo di Fase 4, RINVIATI QUI con il loro motivo**",
]

# ---------------------------------------------------------------------------
# Testi -- paper2_stato.md
# ---------------------------------------------------------------------------

S1_OLD = ("### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **11 settembre 2026**, "
          "quinta revisione")
S1_NEW = ("### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **12 settembre 2026**, "
          "sesta revisione")

S2_OLD = "> **Cosa è cambiato nella quinta revisione (11 settembre) — LA FASE 4 È DECISA.**"
S2_NEW = (
    "> **Cosa è cambiato nella sesta revisione (12 settembre) — LA FASE 5 È CHIUSA.**\n"
    "> Ogni termine del budget porta ora **tre dichiarazioni**: denominatore, base della\n"
    "> percentuale, forma. «Conservativo» è ritirato con la sua ragione, e la dichiarazione ha\n"
    "> trovato ciò che la parola copriva: **due percentuali pubblicate su base sbagliata** (il +309,\n"
    "> che è il 4.30 % del deficit e non l'1–2; la riga snapshot, valore centrale di un nullo), **un\n"
    "> sistematico il cui contrasto apparteneva a un altro sottoinsieme** (36.9 % su 240\n"
    "> configurazioni contro 23.9 % sulle 58 del regime) e **due attribuzioni causali** già\n"
    "> falsificate dalla Fase 4. Da qui **quattro voci nuove per il Paper 1** — P1-10, P1-11, P1-12,\n"
    "> P1-13 — nessuna delle quali tocca il deficit, il suo rango o la scomposizione in persistenza.\n"
    "> **M26 è pubblicato (9 set): nessun erratum**, perché nessuno dei quattro errori trovati è\n"
    "> consequenziale. **Le predizioni smentite non erano due: sono dodici in A, una in A-bis, cinque\n"
    "> in B.** Le practice passano da sei a **sette** e non vanno più nel §6.2 di M26, che è chiuso,\n"
    "> ma in una sezione del Paper 2. Due dei tre residui di Fase 4 sono collocati; il terzo — la\n"
    "> varianza non spiegata — è **rinviato alla Fase 6** (punto 6.8) perché D6 non converge e la\n"
    "> provenienza di `pk_matrix` non è stabilita. Record 60, `freeze_verify` CLEAN a 60/60.\n"
    "\n" + S2_OLD
)

S3_OLD = "| regole con soglia | — | 0 su 6 | 5 su 6 | **6 su 6, e una ritirata** |"
S3_NEW = S3_OLD + "\n\n" + (
    "**Al 12 settembre (sesta revisione):** registro **60 record**, CLEAN a 60/60 · checklist\n"
    "**rev. 3.21** · Fase 4 **decisa** · Fase 5 **chiusa**, 5.1–5.6 tutte fatte · voci per il Paper 1\n"
    "**tredici**, di cui quattro toccano un'affermazione (P1-7, P1-10, P1-11, P1-12) · un residuo\n"
    "**rinviato** alla Fase 6."
)

S4_OLD = "## 3. Il registro degli emendamenti — 55 record"
S4_NEW = (
    "## 3. Il registro degli emendamenti — 60 record\n"
    "\n"
    "### Fase 4 e Fase 5, record 56–60\n"
    "\n"
    "| # | contenuto |\n"
    "|---|---|\n"
    "| 56 | l'ensemble v2 esiste, 2000 realizzazioni per emisfero |\n"
    "| 57 | 4.2b-5 misurata: FALLISCE in entrambi gli emisferi |\n"
    "| 58 | le cinque regole di 4.2a/b/c falliscono; soglie di 4.3b **dichiarate** prima della misura |\n"
    "| 59 | 4.3b ha un esito e FALLISCE: sei regole su sei, la Fase 4 è decisa |\n"
    "| 60 | **la Fase 5 è chiusa**: denominatori dichiarati termine per termine, quattro correzioni al Paper 1, nessun erratum su M26, smentite riclassificate 12/1/5, residuo 3 rinviato alla Fase 6 |"
)

S5_OLD = ("| **Z-P1** | **nove voci PRONTE per il Paper 1** — testo sostitutivo scritto, numeri "
          "verificati, nulla da decidere | **applicazione RINVIATA a dopo la Fase 6** |")
S5_NEW = ("| **Z-P1** | **tredici voci per il Paper 1** — testo sostitutivo scritto, numeri "
          "verificati, nulla da decidere. *Quattro toccano un'affermazione: P1-7 (§9, i «fingers of "
          "God»), P1-10 (§8.1, l'origine del massimo a k=1), P1-11 (§7.2 e Tab. 12, l'origine dei "
          "voxel estremi), P1-12 (§8.2, il contrasto del test differenziale). P1-13 riscrive quattro "
          "righe della Tab. 8. **P1-9 va applicata insieme a P1-11 e P1-13**, che toccano lo stesso "
          "paragrafo e la stessa tabella; **P1-8 insieme a P1-12**, che tocca il §7.4 da due lati.* "
          "| **applicazione RINVIATA a dopo la Fase 6** |")

EDITS_STA = [
    ("S1_intestazione", S1_OLD, S1_NEW),
    ("S2_sesta_revisione", S2_OLD, S2_NEW),
    ("S3_stato_in_una_riga", S3_OLD, S3_NEW),
    ("S4_registro_60", S4_OLD, S4_NEW),
    ("S5_aperti_Z_P1", S5_OLD, S5_NEW),
]

MARKERS_STA = [
    "aggiornato **12 settembre 2026**, sesta revisione",
    "> **Cosa è cambiato nella sesta revisione (12 settembre) — LA FASE 5 È CHIUSA.**",
    "**Al 12 settembre (sesta revisione):** registro **60 record**",
    "## 3. Il registro degli emendamenti — 60 record",
    "| **Z-P1** | **tredici voci per il Paper 1**",
]

FILES = [("checklist", EDITS_CHK, MARKERS_CHK, []),
         ("stato", EDITS_STA, MARKERS_STA, [])]

BOM = b"\xef\xbb\xbf"


class PatchError(Exception):
    pass


# ---------------------------------------------------------------------------
# I/O che preserva BOM e fine riga
# ---------------------------------------------------------------------------

def decode(raw):
    bom = raw.startswith(BOM)
    body = raw[len(BOM):] if bom else raw
    text = body.decode("utf-8")  # solleva se non UTF-8: meglio che indovinare
    n_crlf = text.count("\r\n")
    n_lf = text.count("\n")
    if n_crlf and n_crlf != n_lf:
        raise PatchError(f"fine riga misti: {n_crlf} CRLF su {n_lf} LF; non scrivo")
    nl = "\r\n" if n_crlf else "\n"
    return text.replace("\r\n", "\n"), nl, bom


def encode(text, nl, bom):
    if "\r" in text:
        raise PatchError("CR spuri nel testo normalizzato")
    out = text.replace("\n", nl).encode("utf-8")
    return (BOM + out) if bom else out


def sha(b):
    return hashlib.sha256(b).hexdigest()


def atomic_write(path, data):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".p1_10_", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise



# ---------------------------------------------------------------------------
# Nucleo -- generico su (edits, markers, intatti)
# ---------------------------------------------------------------------------

def delta_atteso(edits):
    return sum(new.count("\n") - old.count("\n") for _, old, new in edits)


def patch_text(text, edits, markers, etichetta):
    present = [m for m in markers if m in text]
    if present:
        raise PatchError(f"{etichetta}: patch già applicata (anche parzialmente): "
                         f"{len(present)} marcatori presenti, primo {present[0][:60]!r}")
    for name, old, _ in edits:
        c = text.count(old)
        if c != 1:
            raise PatchError(f"{etichetta}/{name}: ancora trovata {c} volte (attesa 1)")
    out = text
    for name, old, new in edits:
        out = out.replace(old, new, 1)
    back = out
    for name, old, new in reversed(edits):
        c = back.count(new)
        if c != 1:
            raise PatchError(f"{etichetta}/{name}: testo nuovo trovato {c} volte nel risultato")
        back = back.replace(new, old, 1)
    if back != text:
        raise PatchError(f"{etichetta}: l'inversa non restituisce l'originale: la patch toccherebbe altro")
    d = out.count("\n") - text.count("\n")
    if d != delta_atteso(edits):
        raise PatchError(f"{etichetta}: delta righe {d} contro atteso {delta_atteso(edits)}")
    return out


def verify_text(text, edits, markers, intatti):
    res = []
    for m in markers:
        c = text.count(m)
        res.append((c == 1, f"marcatore presente una volta: {m[:55]!r} -> {c}"))
    for name, old, new in edits:
        c = text.count(new)
        res.append((c == 1, f"{name}: testo nuovo presente una volta -> {c}"))
    for name, old, new in edits:
        if old not in new:  # sostituzioni vere, non inserimenti
            res.append((text.count(old) == 0, f"{name}: testo sostituito assente -> {text.count(old)}"))
    for m in intatti:
        c = text.count(m)
        res.append((c == 1, f"intatto: {m[:50]!r} -> {c}"))
    back = text
    ok_inv = True
    for name, old, new in reversed(edits):
        if back.count(new) != 1:
            ok_inv = False
            break
        back = back.replace(new, old, 1)
    if ok_inv:
        ok_inv = all(back.count(o) == 1 for _, o, _ in edits) and not any(m in back for m in markers)
    res.append((ok_inv, "l'inversa ricostruisce un originale coerente"))
    return res


def _blocchi(percorsi):
    """[(etichetta, percorso, edits, markers, intatti)] per i file passati."""
    out = []
    for (et, edits, markers, intatti) in FILES:
        p = percorsi.get(et)
        if p is not None:
            out.append((et, p, edits, markers, intatti))
    if not out:
        raise PatchError("nessun file indicato")
    return out


# ---------------------------------------------------------------------------
# Comandi
# ---------------------------------------------------------------------------

def cmd_dry_run(percorsi):
    for et, p, edits, markers, _ in _blocchi(percorsi):
        if not os.path.isfile(p):
            raise PatchError(f"file non trovato: {p}")
        raw = open(p, "rb").read()
        text, nl, bom = decode(raw)
        out = patch_text(text, edits, markers, et)
        new_raw = encode(out, nl, bom)
        print(f"\n--- {et}: {p}")
        print(f"  fine riga:    {'CRLF' if nl == chr(13) + chr(10) else 'LF'}   BOM: {bom}")
        print(f"  sha256 prima: {sha(raw)}")
        print(f"  sha256 dopo:  {sha(new_raw)}")
        print(f"  righe: {text.count(chr(10))} -> {out.count(chr(10))} "
              f"(delta {out.count(chr(10)) - text.count(chr(10))}, atteso {delta_atteso(edits)})")
        for name, old, new in edits:
            print(f"    [ok] {name}: ancora unica, +{new.count(chr(10)) - old.count(chr(10))} righe")
        print("    [ok] inversa = originale byte per byte")
    print("\nDRY-RUN OK: nessuna scrittura")
    return 0


def cmd_apply(percorsi):
    blocchi = _blocchi(percorsi)
    # prima si valida TUTTO, poi si scrive: un file rotto non lascia l'altro a metà
    pronti = []
    for et, p, edits, markers, intatti in blocchi:
        if not os.path.isfile(p):
            raise PatchError(f"file non trovato: {p}")
        raw = open(p, "rb").read()
        text, nl, bom = decode(raw)
        out = patch_text(text, edits, markers, et)
        pronti.append((et, p, raw, encode(out, nl, bom), edits, markers, intatti))
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scritti = []
    for et, p, raw, new_raw, edits, markers, intatti in pronti:
        bak = f"{p}.bak_fase5_{stamp}"
        if os.path.exists(bak):
            raise PatchError(f"backup già esistente: {bak}")
        with open(bak, "xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        atomic_write(p, new_raw)
        disk = open(p, "rb").read()
        if disk != new_raw:
            raise PatchError(f"{et}: il file su disco non coincide con quanto scritto")
        text, _, _ = decode(disk)
        bad = [m for ok, m in verify_text(text, edits, markers, intatti) if not ok]
        if bad:
            raise PatchError(f"{et}: verify fallito dopo la scrittura ({bad[0]}); l'originale è in {bak}")
        scritti.append((et, p, bak, sha(raw), sha(new_raw)))
    for et, p, bak, s0, s1 in scritti:
        print(f"\n--- {et}")
        print(f"  backup:  {bak}  sha256 {s0}")
        print(f"  scritto: {p}  sha256 {s1}")
    print(f"\nAPPLY OK: {sum(len(b[2]) for b in blocchi)} modifiche su {len(blocchi)} file, "
          f"verify superato sui file riletti")
    return 0


def cmd_verify(percorsi, quiet=False):
    tot = bad_tot = 0
    for et, p, edits, markers, intatti in _blocchi(percorsi):
        if not os.path.isfile(p):
            raise PatchError(f"file non trovato: {p}")
        text, _, _ = decode(open(p, "rb").read())
        res = verify_text(text, edits, markers, intatti)
        bad = [m for ok, m in res if not ok]
        if not quiet or bad:
            print(f"\n--- {et}: {p}")
            for ok, m in res:
                print(f"  [{'ok' if ok else 'FAIL'}] {m}")
        tot += len(res)
        bad_tot += len(bad)
    print(f"\nVERIFY: {tot - bad_tot}/{tot}" + ("" if not bad_tot else "  -> FALLITO"))
    return 0 if not bad_tot else 1


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _fixture(edits, intatti):
    parts = ["# titolo", ""]
    for m in intatti:
        parts += [m + " x", ""]
    for _, old, _ in edits:
        parts += [old, ""]
    return "\n".join(parts)


def selftest():
    import shutil
    checks = []

    def chk(c, m):
        checks.append((bool(c), m))

    for et, edits, markers, intatti in FILES:
        base = _fixture(edits, intatti)
        out = patch_text(base, edits, markers, et)
        chk(all(m in out for m in markers), f"{et}: tutti i marcatori presenti dopo la patch")
        chk(out.count("\n") - base.count("\n") == delta_atteso(edits), f"{et}: delta righe calcolato = misurato")
        chk(all(ok for ok, _ in verify_text(out, edits, markers, intatti)), f"{et}: verify verde sul fixture")
        try:
            patch_text(out, edits, markers, et)
            chk(False, f"{et}: seconda applicazione rifiutata")
        except PatchError:
            chk(True, f"{et}: seconda applicazione rifiutata")
        for name, old, _ in edits:
            try:
                patch_text(base.replace(old, "XXX", 1), edits, markers, et)
                chk(False, f"{et}/{name} mancante -> rifiuto")
            except PatchError:
                chk(True, f"{et}/{name} mancante -> rifiuto")
            try:
                patch_text(base + "\n" + old + "\n", edits, markers, et)
                chk(False, f"{et}/{name} duplicata -> rifiuto")
            except PatchError:
                chk(True, f"{et}/{name} duplicata -> rifiuto")
        try:
            patch_text(base + "\n" + markers[0] + "\n", edits, markers, et)
            chk(False, f"{et}: marcatore isolato -> rifiuto")
        except PatchError:
            chk(True, f"{et}: marcatore isolato -> rifiuto")
        rotto = out.replace(edits[0][2], edits[0][1], 1)
        chk(not all(ok for ok, _ in verify_text(rotto, edits, markers, intatti)),
            f"{et}: verify rileva la prima modifica mancante")

    tmp = tempfile.mkdtemp(prefix="fase5_selftest_")
    _so = sys.stdout
    try:
        for label, nl, bom in (("LF", "\n", False), ("CRLF", "\r\n", True)):
            perc, raws = {}, {}
            for et, edits, markers, intatti in FILES:
                p = os.path.join(tmp, f"{et}_{label}.md")
                raws[et] = encode(_fixture(edits, intatti), nl, bom)
                open(p, "wb").write(raws[et])
                perc[et] = p
            m0 = {et: sha(open(p, "rb").read()) for et, p in perc.items()}
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
            try:
                cmd_dry_run(perc)
                m1 = {et: sha(open(p, "rb").read()) for et, p in perc.items()}
                rc = cmd_apply(perc)
            finally:
                sys.stdout.close()
                sys.stdout = _so
            chk(m0 == m1, f"{label}: dry-run non scrive nessuno dei due file")
            chk(rc == 0, f"{label}: apply rc=0 su due file")
            for et, p in perc.items():
                raw1 = open(p, "rb").read()
                chk(raw1.startswith(BOM) == bom, f"{label}/{et}: BOM preservato")
                t1 = raw1[3:] if bom else raw1
                if nl == "\r\n":
                    chk(t1.count(b"\n") == t1.count(b"\r\n"), f"{label}/{et}: nessun LF isolato")
                else:
                    chk(b"\r" not in t1, f"{label}/{et}: nessun CR introdotto")
                baks = [f for f in os.listdir(tmp) if f.startswith(f"{et}_{label}.md.bak_fase5_")]
                chk(len(baks) == 1 and open(os.path.join(tmp, baks[0]), "rb").read() == raws[et],
                    f"{label}/{et}: backup identico all'originale")
            prima = {et: open(p, "rb").read() for et, p in perc.items()}
            try:
                cmd_apply(perc)
                chk(False, f"{label}: seconda apply rifiutata")
            except PatchError:
                chk(all(open(p, "rb").read() == prima[et] for et, p in perc.items()),
                    f"{label}: seconda apply rifiutata, entrambi i file intatti")
        # un file valido e uno no: nessuno dei due viene scritto
        pv = os.path.join(tmp, "chk_ok.md")
        pb = os.path.join(tmp, "sta_rotto.md")
        open(pv, "wb").write(encode(_fixture(EDITS_CHK, []), "\n", False))
        open(pb, "wb").write(encode(_fixture(EDITS_STA, []).replace(S3_OLD, "XXX", 1), "\n", False))
        s0 = (sha(open(pv, "rb").read()), sha(open(pb, "rb").read()))
        try:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
            try:
                cmd_apply({"checklist": pv, "stato": pb})
            finally:
                sys.stdout.close()
                sys.stdout = _so
            chk(False, "un file rotto -> nessuna scrittura")
        except PatchError:
            s1 = (sha(open(pv, "rb").read()), sha(open(pb, "rb").read()))
            chk(s0 == s1, "un file rotto -> nessuna scrittura, entrambi intatti")
            chk(not [f for f in os.listdir(tmp) if f.startswith("chk_ok.md.bak")], "nessun backup creato")
        # un solo file passato: si patcha solo quello
        p1 = os.path.join(tmp, "solo_chk.md")
        open(p1, "wb").write(encode(_fixture(EDITS_CHK, []), "\n", False))
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            rc = cmd_apply({"checklist": p1})
        finally:
            sys.stdout.close()
            sys.stdout = _so
        chk(rc == 0 and all(m in open(p1, encoding="utf-8").read() for m in MARKERS_CHK),
            "un solo file passato: patchato quello, senza l'altro")
    finally:
        sys.stdout = _so
        shutil.rmtree(tmp, ignore_errors=True)

    n_ok = sum(ok for ok, _ in checks)
    for ok, m in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {m}")
    print(f"SELFTEST: {n_ok}/{len(checks)}")
    return 0 if n_ok == len(checks) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for c in ("dry-run", "apply", "verify"):
        s = sub.add_parser(c)
        s.add_argument("--checklist", default=None, help="percorso di checklist_paper2.md")
        s.add_argument("--stato", default=None, help="percorso di paper2_stato.md")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    try:
        if a.cmd == "selftest":
            return selftest()
        perc = {k: v for k, v in (("checklist", a.checklist), ("stato", a.stato)) if v}
        return {"dry-run": cmd_dry_run, "apply": cmd_apply, "verify": cmd_verify}[a.cmd](perc)
    except PatchError as e:
        print(f"RIFIUTO: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

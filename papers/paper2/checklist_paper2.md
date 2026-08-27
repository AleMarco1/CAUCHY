# Paper 2 — Checklist di sviluppo, da zero alla scrittura
### rev. 3.5 — 27 agosto 2026 — Fase 2 eseguita: punto di decisione superato, resta il 2.5

> **Base documentale.** M26 R1 (`MN-26-2100-P.R1`, sottomessa 23 ago 2026), Paper 1
> (`MN-26-2388-P`), `canovaccio_paper2.md` rev. 25 ago (sera),
> `canovaccio_4_paper_followup.md` rev. 25 ago (sera).
>
> **Cosa cambia rispetto alla rev. 2.** Le voci nuove o modificate sono marcate **✦**; restano
> marcate **★** quelle introdotte dalla rev. 2 e non toccate.
>
> 1. **Fusione col Paper 5.** Nasce la **Fase 4D — Componente D**, la risposta ai parametri
>    cosmologici. `canovaccio_paper5.md` è archiviato.
> 2. **Fase 1 chiusa in gran parte.** 1.1, 1.2a, 1.3 e il cancello 2.4 sono eseguiti; le tabelle di
>    1.2 e 1.5 sono sostituite dai valori misurati.
> 3. **Quattro scoperte sulla pipeline** che cambiano cancelli e convenzioni: σ_px a runtime,
>    `set_geometry` che non ri-deriva il box, la regola di maschera decodificata, `kind="ran"`.
> 4. **Il gauge della decomposizione** entra come convenzione obbligatoria: le practice passano da
>    tre a cinque.
>
> **Cosa cambia nella rev. 3.1.** Solo la Fase 0, marcata **✧**. La fusione col Paper 5 aveva
> introdotto una fase intera senza passare dai prerequisiti: cinque voci mancavano, due delle quali
> toccano i principi del progetto (etichettatura v1/v2 e pre-registrazione). Inoltre **0.7** è
> spaccato in una parte eseguibile e una di scrittura, e la precondizione di 2.2 sull'origine di
> σ_px migra in **0.5 Q4**, dove appartiene.
>
> **rev. 3.2.** 0.7b migra alla Fase 7 §10 (`paper2_stato.md` registra F0.7 fra i chiusi dal
> 25 agosto); 0.12 è **corretta**, perché annotare dentro il reference ne romperebbe il digest di
> gate; le voci eseguibili passano a `[~]` e hanno uno strumento, `paper2_fase0_close.py`.
>
>
> **Cosa cambia nella rev. 3.4.** Le voci nuove o modificate sono marcate **✧✧**. La Fase 2 è
> entrata in esecuzione e ha prodotto cinque risultati che cambiano voci a monte e a valle:
>
> 1. **2.1 chiuso in quattro parti** (E ensemble, G geometria, D₁ chiusura DESI, P provenienza),
>    strumento `src/paper2_gate21.py`. Δ*N*_H1 = 0 esatto in entrambi gli emisferi.
> 2. **2.1-M, cancello nuovo:** la maschera è riproducibile dai random per **identità di array**.
>    Era la precondizione vera della Fase 3, e non era in checklist.
> 3. **2.1-D₂, cancello nuovo:** il runner di Fase 2 deve chiudere al fiduciale prima che il 2.2 sia
>    interpretabile. Baseline e punto dilatato non possono venire da due codici diversi.
> 4. **3.0 riscritto.** La maschera è caricata da disco in **entrambi** gli emisferi e va riderivata
>    per ogni geometria: è un passo obbligatorio, non un'ipotesi.
> 5. **L'override di σ_px del 2.2 è un moltiplicatore, non un valore assoluto.** La 0.5 Q4 è
>    corretta di conseguenza.
>
>
> **Cosa cambia nella rev. 3.5.** Voci marcate **✧✧✧**. La Fase 2 è stata **eseguita** fino al punto
> di decisione. Quattro esiti e una scoperta:
>
> 1. **2.2b confermato**, Δ = 0 esatto in entrambi gli emisferi. **2.3 confermato**, Δ > 0.
> 2. **2.2a SMENTITO** (+34 NGC, +6 SGC contro ≤ 5). La soglia era calibrata a maschera fissa,
>    prima che il 2.1-M rendesse la maschera mobile. Registrato come smentito, non riparato.
> 3. **Due cancelli nuovi, entrambi nati dalla smentita:** `padladder` (scala di padding a cubo
>    variabile) e `maskladder` (scala di soglia a cubo costante).
> 4. **La scoperta:** *N*_H1 segue il **conteggio dei voxel di maschera**, con elasticità
>    **1.08**, e non la risoluzione. La deriva che il padladder aveva fatto sembrare un pavimento
>    da 1 σ è **correggibile**, e il pavimento vero a cubo costante è **0.03–0.065 σ**.
> 5. **Il gauge a cubo costante è vindicato una seconda volta:** tiene la cella fissa per
>    costruzione, quindi spegne il canale che avrebbe reso la Componente A poco affidabile.
>
> Nessuna fase rimossa; nessun run pianificato annullato.

---

## Fase 0 — Prerequisiti e ri-perimetrazione dello scopo

- [x] **0.1 — Ensemble v1 congelato.** 5 tier, 34 836 file, 26.771 GiB, digest riprodotti. v1 è
      immutabile; ogni numero porta l'etichetta v1 o v2. Mai "ensemble fiduciale" senza suffisso.
      *(Applicazione alla Componente D: vedi 0.9.)*
- [ ] **0.2 — Stato del Paper 1.** Non sottomettere il Paper 2 prima che il Paper 1 sia fuori dal
      secondo giro di referee.
- [x] **0.3 — Componente B ri-perimetrata.** Canovaccio rev. 25 ago.
- [x] **0.4 — Tensione erosione ↔ FKP registrata.** Fattore ~24. Provenienza chiarita (P-B: la scala
      ritirata era priva del livello *k* = 1).
- [x] **✦ 0.5 — Ispezione del codice.**
      1. **Box derivato dai random**, non hard-coded: `derive_box(pos_r, pad=5.0)` riproduce
         *L* = 1997.3629167166155 (NGC) e 1904.4501607158168 (SGC) a 10⁻⁶ relativo.
      2. **σ_px calcolato a runtime** come *R*/Δ*x*, verificato all'ultimo bit
         (5.0/15.604397786848558 = 0.32042249039652254). **La pipeline usa la convenzione in unità
         FISICHE.** Conseguenze in 2.2 e 3.3.
      3. **Maschera ricostruita a runtime.** `v1_fullcube` = densità CIC random pesata > **1% della
         media sul cubo pieno**: soglia = 0.01 × Σ*w*_r/128³, verificata in entrambi gli emisferi
         (0.0200129 con Σ*w*_r = 4 197 016; 0.0085706 con 1 797 384).
         **✧✧ Confermata alla fonte e per identità di array (2.1-M).** La regola è del produttore,
         `phase6_bgs_voxelize.py:182-183`; nel percorso fiduciale la maschera è però **caricata da
         disco**, non ricostruita (`paper1_remap.py:211-214` NGC, `239-247` SGC): la ricostruzione è
         il ramo di ripiego, e nessun numero congelato è passato di lì. **✧✧ Non è un percentile:**
         taglia NGC a P3.914 (307 805 su 320 342 voxel con *field*_r > 0) e SGC a P3.403
         (172 225 su 178 293). Il *«P10»* dichiarato in M26/P1 **non riproduce** la congelata
         (`rev_n4n5_report.json`, `p10_riproduce_congelata: false`): è materia di 0.2, voce R2.6.
- [x] **✧ 0.5 Q4 — CHIUSA.** `paper1_remap.py:230` fa `M.SIGMA_PX = M.R_SMOOTH / cell`: la "costante" è **riassegnata a runtime** dalla cella derivata, quindi la pipeline usa la convenzione **fisica**. E `build_nu(delta, mask, sigma_px)` prende σ_px come **argomento** (riga 171), passato come `M.SIGMA_PX * args.sigma_scale` (riga 673) e registrato in `sigma_px_canonical`/`sigma_px_used` (riga 678): l'override del 2.2 non richiede modifiche al codice. **✧✧ Ma `--sigma_scale` è un
      MOLTIPLICATORE, non un valore assoluto:** passare 0.32042249 non fissa σ_px, lo moltiplica per
      il canonico nuovo. Su cubo dilatato serve `--sigma_scale = Δx_nuovo/Δx_fid` (**1.05 esatto**
      nel 2.2b, **1.049749669929** nel 2.2a). E per il runner di Fase 2 la leva è un'altra ancora:
      `set_geometry` ricalcola `SIGMA_PX = R_SMOOTH/CELL` **sempre** (`phase8:319-321`) con
      asserzione a 10⁻¹⁵ (riga 325), quindi σ_px non è sovrascrivibile e si pilota assegnando
      `R_SMOOTH` **prima** della chiamata. *(Nota: il percorso `--validate` ricalcola σ_px da `R/cell` su entrambi i lati prima di confrontarli, quindi quel controllo è implicato da quello sulla cella e non porta informazione indipendente.)* Testo originale:  È una delle nove costanti geometriche di G1, impostabile da
      `set_geometry`, oppure `data_side` lo ricalcola internamente da `R_SMOOTH/cell`? *(Era la
      precondizione nascosta del cancello 2.2; è una domanda di ispezione del codice e sta qui.)*
      **Da questo dipende dove va l'override** che 2.2 richiede. Se non è impostabile, l'override va
      fatto a valle, sul kernel, e la cosa va scritta nel manoscritto perché cambia cosa significa
      "σ_px fisso in unità di griglia" per chi rifà il lavoro.
- [~] **✧✧✧ 0.6 — Pre-registrazione. SCRITTA, da depositare.** `paper2_prereg_v1.md` v1.0,
      27 ago 2026, in inglese (la leggeranno i referee). Nove sezioni: la regola di decisione di 1.4
      integralmente, la griglia di 1.3 rev. 2, i cancelli di Fase 2 con i due esiti smentiti, il
      budget d'errore a cinque contributi, e la procedura obbligatoria.
      **Resta da fare: il deposito** su Zenodo sotto il concept DOI 10.5281/zenodo.21128856, e il DOI
      di versione citato nel manoscritto. **Nessun run di Fase 3 prima del deposito.**
      *(La sezione di trasparenza 0.10 è il §1 del documento, in testa e non in coda.)*
- [x] **✧ 0.7a — Numerazione delle limitazioni mappata.** M26 R1 va da (i) a (xi); il Paper 2 chiude
      la (ix) e limita la (ii); la (vii) è chiusa da R1; la (xi) in gran parte dal Paper 1 §5.2; la
      (x) è nuova e apre il Paper 3.
      *(La parte di scrittura — dichiarare nel manoscritto quali limitazioni restano aperte dopo il
      Paper 2 — è **migrata alla Fase 7 §10**, dove appartiene: `paper2_stato.md` registra F0.7 fra i
      chiusi già dal 25 agosto.)*
- [x] **✧✧✧ 0.8 — Guardia su `positions()`. CHIUSA.** Applicata: qualunque `kind` diverso da
      `"ran"` cadeva nel ramo `else` e restituiva **i dati** senza errore. Stessa classe di difetto
      della collisione di path che produsse la discrepanza 445/313 nel Paper 1.
      *(Conseguenza sul disegno del runner di Fase 2: il lato dati **non** passa da `positions()`.
      Usa `M.load_desi_data_field()` in NGC e `S.sgc_positions()` in SGC, come `setup_region`, così
      il token dei dati non serve e la trappola non può mordere nemmeno per errore di battitura.)*

### ✧ Voci nuove: la Fase 4D è entrata senza passare dai prerequisiti

- [x] **✧ 0.9 — Etichettare la Componente D come v1, e dichiarare ora se sarà rifatta su v2.**
      D1–D5 leggono `per_mock_*_R5.jsonl` → `base.N_H1`: **sono numeri v1**, ma i record
      `compD_*.jsonl` e `compD_nonlinear_*.jsonl` non hanno un campo `ensemble`. Oggi *n*_s = +0.3976
      è un numero senza suffisso, che è precisamente ciò che 0.1 vieta.
      1. aggiungere `"ensemble": "v1"` allo schema e riscrivere i record in append;
      2. **dichiarare adesso** che D2 verrà ripetuta su v2 quando l'ensemble esiste. Costa minuti, ma
         deciderlo *dopo* aver visto i risultati v1 non è la stessa cosa che deciderlo prima.
- [x] **✧✧✧ 0.10 — Sezione di trasparenza. SCRITTA.** È il **§1 di `paper2_prereg_v1.md`**, in
      testa al documento e non in coda: una sezione di trasparenza in fondo non è trasparenza.
      Elenca per esteso cosa era già in mano al deposito — **Componente D interamente eseguita**
      (D2, D4, D5, D6 con P1 e Q1–Q4 smentite), **Fasi 0–2 eseguite** (2.2a e il padladder smentiti),
      e la correzione dovuta al Paper 1 sull'etichetta «P10» — e chiude dichiarando **cosa era
      genuinamente ignoto**: l'intera misura della Componente A, la simmetria della risposta, la
      completezza sui quattro angoli, e quindi quale dei quattro esiti E1–E4 si verifichi.
      Il §0 dichiara in apertura che il documento pre-registra la **Fase 3 in poi** e non le Fasi 0–2.
- [x] **✧ 0.11 — Erosione allineata. CHIUSA.** `gaussian_filter` sulla maschera float è esattamente il calcolo di w̄ (riga 136), e il 7.8%/0.998 pubblicato è riprodotto. L'erosione usa `distance_transform_edt` (riga 78): a *k* = 1 coincide con l'erosione a sei vicini, diverge per *k* ≥ 2. *(Nota per il manoscritto: `gaussian_filter` usa `mode='reflect'`, il mio calcolo padding a zero; differiscono solo al bordo del cubo, da cui la maschera sta lontana.)* Testo originale:  I run di 1.2b riportano
      `mask_erosion: ASSENTE (uso interna)`: erosione a sei vicini, bordi del cubo come esterno. Ma
      `src/paper1_mask_erosion.py:21` stampa proprio `voxel con w < 0.99   w medio`, cioè calcola le
      stesse due quantità. **Se l'elemento strutturante differisce, i livelli *k* non corrispondono e
      i w̄ di 1.2b non sono confrontabili con quelli del Paper 1.** Cancello: riprodurre la riga
      fiduciale di quello script. Minuti, e va fatto prima di citare i numeri.
- [x] **✧ 0.12 — Procedura di emendamento. CHIUSA e già usata due volte per una ritrattazione.** Reference byte-identico (sha256 `332939bc…` invariato); storia leggibile: valore sbagliato, rettifica, motivo. Se avessi emendato in place, la coincidenza del primo vicino sarebbe sparita senza traccia.
      La formulazione precedente diceva «annotazioni append-only *dentro* il file». Sbagliato:
      qualunque scrittura in `paper2_v1_reference.json` ne cambia `_self_sha256` — che è la costante
      di cancello di mezza toolchain — e il digest del tier `records`. **Emendare rompendo il gate è
      esattamente ciò che l'immutabilità doveva impedire.**
      Regola corretta:
      1. il reference resta **byte-identico**, per sempre;
      2. gli emendamenti vivono in un file sorella append-only, `src/paper2_v1_amendments.jsonl`,
         con `key`, `json_path`, `old_value`, `new_value`, motivo, evidenza, data e lo sha256 del
         reference al momento dell'emendamento;
      3. chi legge **sovrappone** gli emendamenti al reference; nessuno li fonde.
      `paper2_fase0_close.py amend --apply` applica i primi due:
      `practical_rule` → *"sigma_px <~ d_med, d_med = median 1-NN separation in grid units"*, e
      `practical_limit_SGC` = 0.37980, che nel reference **non esisteva**.

- [x] **✧ 0.13 — Congelare gli ingressi della Componente D.** Due file su cui poggiano D2–D6 stanno
      fuori dal congelamento:
      - `data\raw\quijote\3D_cubes\latin_hypercube_nwLH\latin_hypercube_nwLH_params.txt` — sotto
        `data\raw\`, mentre il freeze gira con `--roots results`: **il join di D2 dipende da un file
        non congelato**;
      - `results\phase7_pk_nwlh_cache.npz` — estensione `.npz`, fuori dalle estensioni del tier
        `records`.
      Aggiungere entrambi gli sha256 al reference set. *(Vedi anche D6: la provenienza del cache
      resta da stabilire, ed è un'altra ragione per congelarlo con un'etichetta esplicita.)*

---

## Fase 1 — Triage teorico: cosa può fare l'AP, prima di misurarlo

### 1.1 — Proposizione 2 — **chiusa**

- [x] **1.1a — Enunciato e dimostrazione.** Forma esatta (padding nullo o moltiplicativo, σ_px in
      unità di griglia) e **Proposizione 2′** per il padding additivo dell'implementazione: il
      residuo è una dilatazione attorno al centro del cubo, di fattore
      *a*(α) = α(*E*+2*p*)/(α*E*+2*p*), con max |Δ*u*| = *Np*|1−α|/(α*E*+2*p*) ≤ **1.4 × 10⁻² voxel**.
      Verificata per **quattro vie indipendenti**, l'ultima su 13.2 M random: predice il lato del cubo
      dei punti A1/A3 a 5 × 10⁻⁵ h⁻¹Mpc.
- [x] **✦ 1.1b — Dove si rompe, e quanto.**
      (i) tiling (→ 1.5); (i-bis) gradino discreto di tiling;
      (ii) inversione *r* → *z*_cosmo nel carving; (ii-bis) finestra radiale del pre-filtro
      (+55.26 h⁻¹Mpc solo a Ω_m = 0.25, *w*₀ = −1.2, risolta da `set_geometry`);
      (iii) **padding additivo** — *non* "arrotondamenti CIC", che sono continui e non contribuiscono;
      (iv) convenzione σ_px (→ 2.3);
      **✦ (v) asse dominante del lato del cubo** — voce nuova: sotto *F*_AP l'argmax potrebbe
      cambiare. **Misurata: non cambia**, margine 53.8–53.9% (NGC) e 88.5% (SGC) su tutti i punti.
      *Non sono rotture:* la regola di maschera (convenzione) e l'invarianza monotona (Prop. 1).
- [x] **★ 1.1c — Posizionamento** rispetto a M26 R1 §4.1 e Paper 1 §2.3. La Prop. 2 riguarda il
      **dominio** (identità delle celle), la Prop. 1 il **codominio** (ordine dei valori): componibili
      e da citare in quest'ordine.
- [x] **✦ 1.1d — Lemma 3.** *F*_AP(*r*) = *f*/(*r f*′), costante = *F*₀ **se e solo se**
      *f* = *A r*^(1/*F*₀). Elimina l'ambiguità del *z*_pivot e incastra la Prop. 2 come caso *F* = 1.

### 1.2 — Tabella di triage AP — **ricalcolata**

**✦ Il gauge non è unico.** α_iso da minimi quadrati è una media pesata di *f*/*r*; il residuo varia
di un fattore **4.3** sull'insieme degli α ammissibili. Per la Prop. 2 la parte isotropa è
assorbibile a costo zero, quindi il contenuto fisico è il **minimax di Chebyshev**. Il fit ai minimi
quadrati sovrastima il segnale AP **fino al 26.4%**. Tutti i numeri qui sotto sono in gauge minimax.

| Ω_m | *w*₀ | α_iso (mmx) | res. (h⁻¹Mpc) | *L* | Δ*x* | σ_px | res. (voxel) | asse |
|---|---|---|---|---|---|---|---|---|
| 0.25 | −1.2 | 1.042909 | 8.88 | 2098.82 | 16.3970 | 0.30493 | **0.5411** | y |
| 0.25 | −1.0 | 1.016200 | 3.74 | 2036.36 | 15.9091 | 0.31429 | 0.2349 | y |
| 0.25 | −0.8 | 0.989213 | 1.64 | 1972.91 | 15.4134 | 0.32439 | 0.1067 | y |
| 0.28 | −1.2 | 1.033635 | 6.69 | 2076.41 | 16.2219 | 0.30823 | 0.4122 | y |
| 0.28 | −1.0 | 1.008856 | 2.03 | 2018.65 | 15.7707 | 0.31704 | 0.1284 | y |
| 0.28 | −0.8 | 0.983615 | 2.87 | 1959.55 | 15.3090 | 0.32661 | 0.1876 | y |
| 0.3175 | −1.2 | 1.022531 | 4.14 | 2049.70 | 16.0133 | 0.31224 | 0.2584 | y |
| **0.3175** | **−1.0** | **1.000000** | **0.00** | **1997.3629** | **15.60440** | **0.320422** | **0.0000** | y |
| 0.3175 | −0.8 | 0.976840 | 4.37 | 1943.36 | 15.1825 | 0.32933 | 0.2878 | y |
| 0.35 | −1.2 | 1.013297 | 2.10 | 2027.63 | 15.8409 | 0.31564 | 0.1325 | y |
| 0.35 | −1.0 | 0.992597 | 1.66 | 1979.63 | 15.4658 | 0.32329 | 0.1073 | y |
| 0.35 | −0.8 | 0.971141 | 5.62 | 1929.75 | 15.0762 | 0.33165 | 0.3728 | y |

**✦ Convenzione di *F*_AP.** L'escursione «0.974–1.041» che circolava è α_∥/α_⊥. Nella convenzione
standard *D*_M *H*/*c*, cioè α_⊥/α_∥, è **0.9611–1.0268** puntuale e **0.973–1.019** in *F*
efficace. Va dichiarata con la formula, non col nome.

- [x] **✦ 1.2a — Ricalcolo col box effettivo.** Fatto: `paper2_item12a_geom.py`, 18 punti per
      emisfero, cancello fiduciale a 2.9 × 10⁻⁹. Colonne nuove: asse dominante, α_box, Δ*x* effettivo.
      **α_box ≠ α_iso** di ~2 × 10⁻⁴, che è esattamente la Prop. 2′.
- [x] **✦ 1.2b — w̄ e *d*_med misurati, per punto e per regione.** 11 geometrie per emisfero,
      cancello `data_side` a 2.9 × 10⁻⁹ (NGC) e 2.2 × 10⁻⁹ (SGC).
      - **✧ *d*_med identificato ESATTAMENTE, dopo una ritrattazione.** È la **mediana della
        distanza euclidea dal bordo della maschera**, in unità di griglia — `distance_transform_edt`,
        come importa `paper1_mask_erosion.py:78`, e come dice in chiaro la riga 19 dello stesso file
        (*"il footprint NGC ha profondità mediana di soli 3 voxel"*).
        **NGC = 3.000 voxel esatti → 3/9 = 0.33333 contro il congelato 0.333, scarto +0.0003.**
        SGC = 2.828 = 2√2 esatto → limite **0.31422**. **Il "/9" è letterale e va mantenuto.**
        *Ritrattata l'identificazione precedente con la mediana della distanza al primo vicino
        (0.33126 contro 0.333): era una coincidenza numerica, ed era stata presa per una prova.*
      - **w̄ ≥ 0.99 non esclude nulla:** minimo 0.99524 (SGC C4). Il valore fiduciale NGC
        **riproduce la tabella pubblicata del Paper 1**: 7.8% di voxel sotto soglia e w̄ = 0.998
        (misurato: 0.0780 e 0.99799).
      - **Ma la media nasconde una scalinata.** A *k* = 0 la frazione sotto soglia salta a gradini in
        σ_px (soglie a **0.3075** e **0.33023**, dove basta rispettivamente un vicino in meno). NGC va
        da 0.034 a 0.152, SGC da 0.091 a 0.179, con 9 punti su 11 sopra il gradino principale.
      - **A erosione *k* = 1 la scalinata sparisce:** frac < 0.99 = 0 e *w*_min ≥ 0.99933 ovunque.
        **→ griglia AP a *k* = 1 come primaria** (3.1 e 3.6); *k* = 0 per l'aggancio a v1.
        Costo −15.5% voxel NGC, −17.8% SGC, uniforme e innocuo per una misura differenziale.
      - **✧ Compatibilità dell'erosione (0.11):** l'erosione interna a sei vicini rimuove per un
        passo esattamente i voxel con un vicino di faccia fuori maschera, cioè quelli con EDT = 1.
        **A *k* = 1 coincide quindi con EDT > 1, che è la definizione del Paper 1**; diverge solo per
        *k* ≥ 2. I numeri a *k* = 1 sono confrontabili; quelli a *k* = 2, 3 no.
- [x] **✧ 1.2c — Regola di esclusione, riscritta dopo la rettifica.**

      | | *d*_med | limite | σ_px fid. | margine | punti sotto |
      |---|---|---|---|---|---|
      | NGC | 3.000 | 0.33333 | 0.32042 | +3.9% | **0 / 11** |
      | SGC | 2.828 | 0.31422 | 0.33606 | **−6.9%** | **11 / 11** |

      - **NGC:** criterio di esclusione utilizzabile, e **non esclude nulla**. Margine minimo C4
        +0.5%. *(La versione precedente escludeva C4: era conseguenza dell'identificazione errata.)*
      - **SGC: il limite pratico è violato ovunque, fiduciale compreso.** Non è utilizzabile come
        criterio di esclusione — escluderebbe un risultato pubblicato. Diventa un **caveat
        dichiarato**, e il rimedio operativo è l'erosione.
      - **Perché il sud è più difficile, e va scritto:** footprint più sottile (2.828 contro 3.000
        voxel, +6.1%) **e** cella più piccola (14.879 contro 15.604, quindi σ_px = *R*/Δ*x* più
        grande, +4.9%). I due effetti si sommano: ~11%.
      - **Cosa NON significa.** Il criterio primario del Paper 1 è w̄ ≥ 0.99, e SGC lo supera
        (0.99642). Il limite σ_px ≲ *d*_med/9 è un'**euristica** sulla contaminazione di bordo; il
        test **diretto** è l'erosione, che il Paper 1 ha eseguito e che il deficit SGC ha superato.
        **L'euristica segnala il sud, il test diretto lo assolve** — e va raccontato così, perché un
        referee che ricalcolasse `practical_limit_SGC` arriverebbe allo stesso −6.9% senza contesto.
      - **✧ Errore di categoria da evitare:** applicare il limite alla maschera **erosa** non ha
        senso. L'erosione assottiglia il footprint, quindi *d*_med scende e il criterio peggiora
        formalmente, mentre i voxel contaminati sono stati rimossi — che era lo scopo. **Il limite è
        una diagnostica sulla maschera a *k* = 0.**
      - **Osservazione sul Paper 1, per la discussione o la nota correttiva:** nel reference set
        esiste solo `practical_limit_NGC`. Non manca per svista — **non è mai stato calcolato**, e
        calcolarlo avrebbe segnalato l'emisfero sud.

### 1.3 — Griglia definitiva — **chiusa**, tre blocchi

- [x] **✦ Blocco A — linea α_iso pura** (*F*_AP = 1), test di chiusura: A1 = 0.9725, A2 = fiduciale,
      A3 = 1.0406. **Solo lato dati**, niente ensemble mock.
- [x] **✦ Blocco B — linea *F*_AP pura** (α_iso = 1), campionata a residuo **minimax equispaziato in
      voxel** e simmetrica: *F* ∈ {0.971070, 0.985396, 1.000000, 1.014889, 1.030071}, residui
      {0.569, 0.284, 0, 0.284, 0.569} voxel NGC. La simmetria compra un test non previsto: *N*_H1
      risponde al **segno** della distorsione o solo alla sua **ampiezza**?
- [x] **✦ Blocco C — quattro angoli, che NON sono controlli.** La famiglia (α_iso, *F*_AP) **non è
      completa**: al peggiore degli angoli lascia **0.082 voxel** non modellati, il 14.5%
      dell'ampiezza e 6× l'artefatto di padding. Gli angoli sono l'unico posto dove il terzo canale è
      misurabile: **mock appaiati come per il blocco B**.
- [x] **✧✧✧ 1.3a — Test di convenzione su `make_dc_tab_ap`. CHIUSO.** La convenzione della pipeline
      è **α_∥/α_⊥**, cioè il **reciproco** dello standard. Tutta la griglia dell'item 1.3 rev. 2 è
      espressa in quella convenzione (*p* = *F*_AP pipeline), con la colonna «*F* standard ⊥/∥»
      accanto per la lettura esterna. **Nel manoscritto va dichiarata esplicitamente:** riportare un
      *F* nella convenzione sbagliata inverte il segno della risposta AP.
- [x] **✧✧✧ 1.3b — Test di completezza. DICHIARATO** (l'esecuzione è Fase 3). Confluito nel §6
      dell'item 1.4 e nel **§5.6 della pre-registrazione**.
      **✧✧✧ Soglia corretta: 53 generatori, non «σ_Δ ≈ 250».** La 250 era la dispersione per singola
      realizzazione; il test confronta **medie su *N* = 200 coppie**, quindi la soglia giusta è la
      stessa della rilevabilità, 3σ_Δ/√200 = 53. La vecchia era conservativa di un fattore √200 ≈ 14.
      **Il test ha una firma dichiarata:** deve fallire dove il terzo canale è grande (0.082 voxel a
      C1, 0.047 a C4) e **non** dove è piccolo (0.006 e 0.005). Fallire ovunque, C2 e C3 compresi,
      significa tiling o ri-randomizzazione, non terzo canale.

**Costo:** 8 geometrie complete + 2 run di sola chiusura, contro le 12 del piano originale.

### ✧✧✧ 1.4 — Regola di decisione. CHIUSA e depositata

Fissata per intero in `paper2_item14.md` e trasfusa nel **§5 della pre-registrazione**. *N* = 200
coppie per punto; σ_Δ = 250.5 per realizzazione; **rilevabilità 53**, **rilevanza 390 (NGC) e
206 (SGC)**; quattro esiti E1–E4; range fisico |*F*−1| ≤ 0.027 contro una copertura della linea B di
0.0301. Statistica primaria *N*_H1 a erosione *k* = 1, con **rango empirico**, non z parametrico.

**✧✧✧ La soglia «3σ_Δ ≈ 750» di questa voce è RITIRATA.** Era la 3σ per **singola realizzazione**
invece che sull'errore della media, quindi conservativa di un fattore √200 ≈ 14. Restava qui in
contraddizione con l'item 1.4 e con il documento depositato.

**✧✧✧ E la distinzione che regge tutto:** l'AP agisce su **entrambi** i lati, quindi se dati e mock
rispondono allo stesso modo la risposta **si cancella in *D***. La quantità di interesse è
∂*D*/∂*F*_AP, **non** ∂*N*_H1/∂*F*_AP, che può essere grande senza che *D* si muova di un generatore.
Vanno riportate entrambe, separatamente: confonderle è l'errore più facile di questo paper.
- [x] **✧✧✧ 1.4a — Convenzione di σ_px. CHIUSA: la domanda si è dissolta.** Nel gauge a cubo
      costante *L* è fisso, quindi Δ*x* è fisso, quindi σ_px è **costante su tutti e nove i punti**
      (escursione relativa 5.9 × 10⁻¹⁴ NGC, 3.7 × 10⁻¹⁴ SGC). La regola a runtime (*R*/Δ*x*, unità
      fisiche) e la convenzione in unità di griglia del Paper 1 §8.3 **danno lo stesso numero**. Non
      è una scelta risolta: è una scelta resa vuota dal gauge.
      L'1.64% picco-picco di questa voce si riferiva alla **vecchia** linea B, sostituita dall'item
      1.3 rev. 2. I due numeri restano nel manoscritto per quantificare la posta per chi lavori in un
      gauge diverso: **1.64%** dentro una griglia AP, **40%** fra suite con celle di dimensione
      diversa.
      **Dove la questione sopravvive:** nei cancelli 2.2 e 2.3, che dilatano deliberatamente. Lì
      l'override è necessario e si pilota da `R_SMOOTH` (0.5 Q4), non da σ_px.
- Soglia e convenzione dichiarate qui, non rinegoziabili a run in corso.

### ★ 1.5 — Il confondente di tiling

Il cubo scala con α_iso mentre la scatola Quijote resta a 1000 h⁻¹Mpc. Continuo: frazione
indipendente 0.76 → **0.70 (misurata)** → 0.62. Discreto: a α_iso ≳ 1.001 il lato supera
2000 h⁻¹Mpc e il numero di offset interi cambia — **un gradino**, non un andamento liscio.

**✦ Beneficio della riparametrizzazione:** il tiling dipende da α_iso e non da *F*_AP, quindi lungo
**tutto il blocco B** (α_iso = 1) la molteplicità è **costante**. Il blocco che porta il segnale è
quello immune al confondente.

- [x] **✧✧ 1.5a — CHIUSA, e il 3 contro 5 non era una discrepanza.** `offsets` (`phase8:652-655`)
      usa `floor(lo/L)` e `floor(hi/L)` sugli estremi del cubo: coi valori fiduciali dà **3 offset
      per asse** su tutti e tre gli assi, cioè 27 traslazioni candidate, 15 con almeno una galassia
      dentro. Il **5** di M26 §5.6 è `max_multiplicity` nel reference, cioè quanti voxel di survey
      cadono sulla **stessa cella della scatola**: oggetto diverso. I conti del reference chiudono
      (307 805/214 215 = 1.4369 ≈ `mean_multiplicity` 1.44; 214 215/307 805 = 0.696 =
      `independent_volume_frac`). Nota terminologica obbligatoria prima di citare.
      *(Residuo: la consegna misura frazione indipendente 0.7111–0.7125 contro 0.696 del reference,
      2% da attribuire. Non blocca.)*
      **✧✧ Il 3.2b è già fatto:** `tiling.replica_randomised` su 100 mock dà spostamento della media
      **−13 generatori** (0.037% contro un deficit di 7181) e rapporto di dispersione 0.97. Il tiling
      non è l'anomalia.

---

## Fase 2 — Cancelli prima di ogni misura nuova

- [x] **✧✧ 2.1 — CHIUSO in quattro parti**, 27 ago 2026, strumento `src/paper2_gate21.py`,
      registro `results/paper2/gate21.jsonl`.
      - **2.1-E ensemble.** *n* = 2000, 0 record scartati; media e sd (**ddof = 1**,
        `paper2_compD_partialcorr.py:275`) a **rel 0.000e+00** contro i valori a precisione piena dei
        record del Paper 1: 35 436.686 / 312.9891651683112 e 18 712.9675 / 197.7873817207103.
        *(Confermati per tre vie indipendenti: `paper1_remap_*_R5.json`, il gate della Componente D,
        il blocco `incertezze` di `rev_n4n5_report.json`.)*
        **Riferimento operativo = Paper 1.** M26 (`frozen_reference.mock_baseline` 35 467.15 /
        18 693.595) è **superseded**: scarto ∓0.10 σ **con segno opposto nei due emisferi**, firma
        della collisione di percorsi. Fuori dal verdetto, citato per memoria.
        *(Trappola di arrotondamento: la media SGC vale 18 712.9675 e la checklist ne cita
        l'arrotondamento 18 712.968. Lo scarto è esattamente mezzo ULP, quindi una tolleranza
        `≤ 5e-4` fallisce per 1.9 × 10⁻¹⁴ e `round()` binario dà ...967. Confrontare sui valori
        pieni con tolleranza relativa, e arrotondare con `Decimal`/`ROUND_HALF_UP`.)*
      - **2.1-G geometria.** Box, cella, σ_px canonico e usato a rel 0.00e+00; `sigma_px_used ==
        sigma_px_canonical` bit-identici, cioè il run fiduciale girò a `--sigma_scale 1.0`.
      - **2.1-D₁ chiusura DESI.** `--stage selfcheck` → **28 256 / 15 122, Δ = 0 esatto**, 16.5 s per
        emisfero. I due cancelli interni del sorgente passano a `max|diff| = 0.000e+00` contro
        soglie di 10⁻⁶ e 10⁻⁹: la replica non è compatibile col modulo, è identica.
        **Il messaggio «test di chiusura SUPERATO» del sorgente NON è il verdetto:** quel ramo lo
        stampa anche con `sigma_scale != 1.0` e non esce mai con codice ≠ 0.
      - **2.1-P provenienza.** 11 file protetti, digest invariati prima e dopo ogni run. Il reference
        è byte-identico al congelato (`332939bc…`): l'immutabilità è verificata, non asserita.
      **✧✧ Perché Δ = 0 e non una tolleranza.** Il 2.2a predice |Δ*N*_H1| ≤ 5 generatori, cioè
      0.018%. Una deriva di codice di 2–3 generatori starebbe alla stessa scala del segnale e
      renderebbe il 2.2 non interpretabile.
- [x] **✧✧ 2.1-M — Maschera riproducibile dai random. CHIUSO**, strumento `src/paper2_gate21m.py`.
      `field_r > 0.01 * field_r.mean()` riproduce la congelata per **`np.array_equal` vero** in
      entrambi gli emisferi: soglia a rel 2.2 × 10⁻⁸ / 7.0 × 10⁻⁸, voxel **307 805 / 172 225** esatti.
      *(M2 senza M3 sarebbe un fallimento, non un successo parziale: stesso conteggio in posti
      diversi è la firma di random diversi.)*
      **Perché era la precondizione vera della Fase 3.** La maschera è un array in **spazio di
      indici** caricato da disco; sotto geometria iniettata il box e i campi cambiano e `np.load`
      restituisce lo stesso array. Nel gauge a cubo costante la griglia non si muove e si muovono le
      galassie, di 0.1–0.6 voxel, contro un bordo statico: è la contaminazione di bordo che ha già
      fatto ritirare tre risultati. Ora la maschera si può far muovere con la geometria.
      **✧✧ D3, sottoprodotto che sblocca il runner.** `set_geometry(box_min, box_size)` riproduce la
      riassegnazione manuale di `paper1_remap.py:229-230` a **rel 0.00e+00** su box, cella e σ_px.
      La via sanzionata è bit-identica alla manuale a cosmologia fissa, quindi è legittima anche
      sugli angoli C1–C4, dove la manuale è sbagliata per costruzione (`phase8:167-169`).
      **✧✧ Filo aperto, non bloccante:** peso FKP medio 0.3168 (NGC) e 0.3308 (SGC) contro lo 0.309
      di P1 §4.1. Che i due emisferi differiscano esclude che 0.309 li copra entrambi. È lo stesso
      peso che entra nell'ensemble v2 (4.2a), quindi va chiuso prima dei Paper 3 e 4.
- [x] **✧✧✧ 2.1-D₂ — Chiusura del runner di Fase 2. CHIUSO.** `paper2_runner_fase2.py d2` a
      geometria fiduciale dà **28 256 / 15 122, Δ = 0 esatto**, con `n_valid_voxels` 307 805 /
      172 225 e σ_px a rel 0.00e+00. 12.2 s e 9.9 s; zero random clippati da `cic_3d`.
      **Precondizione del 2.2, ora soddisfatta:** baseline e punto dilatato vengono dallo stesso
      codice, quindi il Δ misura geometria e non differenza fra implementazioni.
      **✧✧✧ La leva `R_SMOOTH` compensa esattamente:** al fiduciale il box esce a rel 2.9 × 10⁻⁹ dal
      congelato (residuo della tabella a 4001 nodi), quindi `R_SMOOTH` non è 5.0 ma 4.999999986 —
      e σ_px torna identico al congelato fino all'ultimo bit. La convenzione è «σ_px bloccato», non
      «*R* bloccato», e la leva la realizza anche quando la cella deriva.
      *(Chiude il filo aperto sull'ancoraggio a griglia rada: quel 2.9 × 10⁻⁹ vale 3.7 × 10⁻⁷ voxel
      e non muove un solo generatore su 28 256. Misurato, non più stimato.)*
- [x] **✧✧✧ 2.2 — Cancello della dilatazione. ESEGUITO**, 27 ago 2026, strumento
      `src/paper2_runner_fase2.py`, registro `results/paper2/fase2.jsonl`. α = 1.05.
      **L'override di σ_px si pilota da `R_SMOOTH`, assegnato PRIMA di `set_geometry`** (0.5 Q4):
      esce 5.25 esatto nel 2.2b e 5.2487 nel 2.2a, e σ_px resta bloccato a 0.32042249 entro 10⁻¹².
      - **2.2b** `pad = 5.0 * alpha_iso` → **Δ = 0 esatto, NGC e SGC. CONFERMATO.**
        Il timore dichiarato prima del run (una galassia su un bordo di cella basterebbe a
        rompere l'invarianza in virgola mobile) non si è materializzato.
        **Ma l'esito non dice nulla sulla Fase 3:** con `pos → α·pos` e `box_min → α·box_min`
        il rapporto (pos − box_min)/cell è invariante bit a bit, gli indici non si muovono, e una
        maschera in spazio di indici resterebbe corretta **per caso**.
      - **2.2a** padding additivo → **+34 (NGC), +6 (SGC). SMENTITO** (predizione ≤ 5).
        La predizione era motivata dalla continuità del CIC **a maschera fissa**, ed è stata
        formulata prima che esistesse il 2.1-M. Il padding additivo lascia il box più corto di
        0.5 h⁻¹Mpc di quello proporzionale: disallinea griglia e galassie di 0.031 voxel, e la
        soglia della maschera è un taglio netto. **Maschera: 307 805 → 308 021 e 172 225 → 172 364.**
      - **✧✧✧ Diagnostica di attribuzione** (`--mask frozen`, deliberatamente ciò che il 3.0
        vieta): a maschera bloccata Δ = **+23 (NGC)** e **−12 (SGC)**. Per differenza, i due canali:

        | | canale maschera | residuo a maschera ferma |
        |---|---|---|
        | NGC | +11 | +23 |
        | SGC | +18 | −12 |

        Il canale maschera ha **lo stesso segno** nei due emisferi; il residuo no. Il bordo non si
        espande, si **rimescola**: NGC 335 voxel entrano e 119 escono, SGC 218 e 79.
        *(Questo scioglie l'apparente anomalia «SGC muove più maschera e meno anelli»: era la somma
        di due canali di segno opposto.)*
- [x] **✧✧✧ 2.3 — Cancello di σ_px. CONFERMATO.** Stessa dilatazione, `R_SMOOTH` = 5.0, σ_px libero
      di seguire la cella (0.320422 → 0.305237 NGC; 0.336055 → 0.320132 SGC, −4.74% identico).
      Δ = **+391 (NGC)** e **+254 (SGC)**, entrambi > 0.
      **✧✧✧ Il canale isotropo è isolato per costruzione:** 2.3 e 2.2a hanno geometria e maschera
      identiche, cambia solo `R_SMOOTH`, quindi la differenza **è** il canale.
      **+357 (NGC)** e **+248 (SGC)**, cioè +1.263% e +1.640%.
      **Elasticità di σ_px: −0.267 (NGC) contro −0.346 (SGC)**, SGC il 30% più sensibile —
      coerente con l'occupazione minore (0.4786 contro 0.7070 gal/voxel), campo più dominato dallo
      shot noise, più anelli guadagnati quando si liscia meno. **Numero riportabile.**
      *Nota di taratura: α = 1.05 è fuori dall'intervallo fisico (|1−α| ≤ 0.0406); il numero da citare
      nel manoscritto va valutato agli α della griglia.*
- [x] **✧✧✧ 2.6 — `padladder`: scala di padding a cosmologia fiduciale. ESEGUITO, predizione
      SMENTITA.** Nove pad da 5.0 a 9.0, spostamento di griglia fino a 0.51 voxel, cioè tutta la
      linea B senza estrapolare. Predizione dichiarata: dispersione ≤ 0.25 σ. Osservato **1.00 σ
      (NGC)** e **1.36 σ (SGC)**.
      **Ma non è jitter: è una deriva monotona**, e *N*_H1 scende **insieme al conteggio dei voxel**
      (NGC −1.108% contro −1.050%; SGC −1.779% contro −1.144%). Un pad più grande allarga il cubo,
      la cella cresce, lo stesso volume occupa meno voxel. La predizione era formulata pensando a
      uno scarto senza segno, sulla base del residuo del 2.2a a maschera ferma: sbagliata.
- [x] **✧✧✧ 2.7 — `maskladder`: scala di soglia a CUBO COSTANTE. ESEGUITO, predizione CONFERMATA.**
      Otto moltiplicatori da 0.005 a 0.025, cella costante a **zero esatto**, voxel mossi del 2.2%.
      Separa «*N*_H1 segue i voxel» da «segue la cella», che nel padladder sono collineari.

      | | pendenza d*N*_H1/d*V* | padladder | compatibilità |
      |---|---|---|---|
      | NGC | **0.1009 ± 0.0016** (*r* = 0.9992) | 0.0897 ± 0.0100 | 1.11 σ |
      | SGC | **0.0945 ± 0.0036** (*r* = 0.9950) | 0.1137 ± 0.0113 | 1.62 σ |

      **Il regressore è il conteggio dei voxel, non la risoluzione.**
      - **✧✧✧ Elasticità 1.098 ± 0.017 (NGC) e 1.074 ± 0.041 (SGC):** *N*_H1 ∝ *V*^1.08,
        **super-lineare**. NGC a 5.6 σ da 1, SGC a 1.8 σ, i due concordano. Non è pipeline: i voxel
        aggiunti al bordo portano più anelli della media. **Vale un paragrafo nel manoscritto.**
      - **✧✧✧ Il criterio del test è stato riscritto prima di girarlo.** «Entro il 20%» era più largo
        dell'incertezza della pendenza di riferimento (nota al 10–11%) e non poteva decidere;
        sostituito con compatibilità a 2 σ combinati. E la scala 0.007–0.014 non aveva leva: col
        rumore atteso avrebbe dato la pendenza al 23%. Allargata a un fattore 5.
      - **✧✧✧ NON c'è asimmetria fra emisferi.** Il 29% del padladder era rumore: le pendenze
        precise differiscono di **1.62 σ**, e col segno opposto. La regolarità NGC/SGC resta a due
        misure (elasticità di σ_px, rendimento di bordo), non tre.
      - **✧✧✧ Limite di validità.** Applicando questa pendenza ai dati del padladder l'escursione
        scende da 313 a 89 (NGC) e da 269 a 83 (SGC), ma **resta una tendenza residua** contro i
        voxel, −0.0112 ± 0.0016 e +0.0192 ± 0.0036, di **segno opposto** nei due emisferi. È un
        secondo canale, quasi certamente la cella, che il maskladder per costruzione non vede.
        **La correzione su `n_valid_voxels` vale a cella fissa, non in generale.**
- [x] **✦ 2.4 — Cancello di monotonia. CHIUSO:** *f*(*r*) strettamente crescente su *z* ∈ [0.1, 0.4]
      in **12/12** punti.
- [ ] **2.5 — Cancello di appaiamento.** Stessi semi per HOD, downsampling radiale e tassellazione;
      a geometria fiduciale il run appaiato riproduce il mock v1 galassia per galassia.
      **✧✧✧ È l'unica voce di Fase 2 ancora aperta**, ed è l'unica che tocca il lato mock: tutti i
      cancelli 2.1–2.7 sono di solo lato dati e costano 10–12 s a run.

**→ ✧✧✧ PUNTO DI DECISIONE SUPERATO, 27 ago 2026.** Il canale isotropo è misurato e isolato
(+357 / +248), la deriva geometrica è **correggibile** e non una barra d'errore, e il pavimento
irriducibile nel regime che conta vale **0.03–0.065 σ**. La Componente A regge e si procede.

### ✧✧✧ Pavimenti misurati, per regime

| regime | NGC | SGC | quando si applica |
|---|---|---|---|
| cubo variabile, dopo regressione sui voxel | 31.8 gen (0.102 σ) | 21.5 gen (0.109 σ) | mai, nel disegno attuale |
| **cubo costante** | **10.1 gen (0.032 σ)** | **12.8 gen (0.065 σ)** | **griglia dell'item 1.3 rev. 2** |

Il gauge a cubo costante tiene *L*, Δ*x* e σ_px fissi per costruzione, quindi il pavimento che entra
nella Componente A è quello di sotto. **È il quarto confondente che quel gauge spegne**, e non era
nell'argomentazione originale dell'item 1.3: va aggiunto alla difesa del gauge nel manoscritto.

---

## Fase 3 — Componente A: sensibilità alla cosmologia fiduciale

- [ ] **✧✧ 3.0 — Sequenza di iniezione, riscritta.** Sette passi, in quest'ordine. Ognuno è
      obbligatorio per una ragione misurata, non per prudenza.
      ```
      R_SMOOTH = sigma_target * cell_fid    # PRIMA: set_geometry ricalcola SIGMA_PX alla riga 321
      set_geometry(z_tab=, dc_tab=)         # comoving_distance e' fra le globali riassegnate
      positions(region, "ran")              # kind="ran" hard-coded: ogni altro token da' i DATI
      derive_box(pos_r, pad=5.0)            # oppure box fiduciale forzato, nel gauge a cubo costante
      set_geometry(box_min=, box_size=)     # CELL e SIGMA_PX ricalcolate e asserite (319-325)
      mask = field_r > 0.01*field_r.mean()  # RIDERIVATA, mai np.load: 2.1-M
      build_field(...) -> compute_tda_features(..., masked=True)
      ```
      - **`set_geometry` non ri-deriva il cubo** (ma ricalcola cella e σ_px): iniettando una tabella
        deformata *D*_C cambia e il box resta al valore fiduciale. Nel run SGC il box in memoria era
        ancora quello NGC.
      - **✧✧ La maschera va riderivata.** È caricata da disco in **entrambi** gli emisferi ed è un
        nodo condiviso da ~30 script (tutti i `paper1_rev_*`, sei `phase6`, `phase8`, otto `phase9`,
        alcuni via `rglob` senza percorso fisso). **Mai rigenerarla sul posto:** il file riderivato
        va su un nome nuovo e il confronto avviene in memoria.
      - **✧✧ `masked=True` non è il default** della firma (`phase8:520`): dimenticarlo dà la
        variante rotta, non un errore.
      - **✧✧ Costruire le deformazioni per rapporti**, mai integrando da zero. La costante del modulo
        (*c* = 299792.0 contro 299792.458) vale 1.53 × 10⁻⁶, cioè 1.06 × 10⁻⁴ voxel a *D*_C massimo:
        2700 volte sotto il più piccolo segnale della linea B (0.2844 voxel), e allo stesso ordine
        del residuo di ancoraggio su griglia rada. Trascurabile, ma il rapporto lo azzera.
      - **✧✧ `cic_3d` ritaglia in silenzio** (`phase8:495-508`): le posizioni fuori dal cubo non
        vengono scartate, vengono **impilate sulle facce**. Contare quante finiscono clippate.
      - **✧✧ Sugli angoli C1–C4 la riassegnazione manuale è vietata.** `phase8:167-169`:
        `phase9_sgc_likeforlike` ne riscrive quattro a mano e funziona perché cambiava geometria a
        **cosmologia fissa**; il Paper 2 cambia cosmologia, quindi tocca anche `OMM`, `OML`,
        `_DC_TAB`, `D_C_ZMIN`, `D_C_ZMAX`. Si passa da `set_geometry`, sempre.
      - **✧✧ Ω_m e *w*₀ della griglia sono etichette della deformazione, non lo stato del modulo.**
        Il modulo lo stampa da sé: *«dc_tab iniettata; OMM/OML non descrivono più la mappatura e non
        vanno riportati come cosmologia»*. Ripeterlo alla lettera nel manoscritto.
      - **Farlo commuta automaticamente σ_px alla convenzione fisica**: applicare qui la decisione
        di 1.4a.
      - **✧✧ La scala nulla si sovrascrive da sola.** `null_ladder_{region}_n{N}.npy`
        (`paper1_remap.py:449`) non porta tag né geometria, e la condizione di riuso (455) include
        `Q.size == mask.sum()`. Una maschera diversa innesca ricalcolo e `atomic_save_npy` sul
        bersaglio congelato del Paper 1. È in `PROTECTED` di `paper2_gate21.py`: lanciare
        `snapshot` prima e dopo ogni run di Fase 3.
- [ ] **3.1 — Lato dati** per ogni punto sopravvissuto a 1.2c (dieci: undici meno NGC C4).
      Ricalcolare da capo *r*(*z*), box, Δ*x*, maschera, σ_px, α. Output: *N*_H1, β₁(ν), erosione
      *k* = 0–3, w̄, *d*_med, occupazione.
      **✧ Livello primario: *k* = 1**, per la scalinata di 1.2b; *k* = 0 riportato in parallelo.
- [ ] **3.2 — Lato mock, appaiato.** *N* = 100–200 per punto, stessi semi. Carving rifatto per intero.
      Registrare **quante galassie cambiano stato di selezione**: è la misura diretta della rottura
      (ii) di 1.1b.
- [ ] **★ 3.2a** Molteplicità di tiling per punto (`x mod L_box`).
- [ ] **★ 3.2b** Randomizzazione delle repliche su **tutti** i punti, non solo il fiduciale.
- [ ] **★ 3.2c** Se il gradino sopravvive alla randomizzazione: **artefatto di costruzione**, non
      derivata.
- [ ] **✧✧✧ 3.3 — Decomposizione, ora a CINQUE contributi.** Il quinto è nuovo e misurato in
      Fase 2: **(e) conteggio dei voxel di maschera.** Si **SOTTRAE**, non si somma in quadratura:
      è una funzione nota, Δ*N*_H1 − *s* · Δ*V*, con *s* = **0.1009 (NGC)** e **0.0945 (SGC)**.
      In quadratura entra solo il residuo: **10 generatori (NGC), 13 (SGC)**.
      **Limite di validità dichiarato:** vale a cella fissa. Sui nove punti del gauge a cubo
      costante la cella è fissa per costruzione, quindi vale; per un eventuale punto a cubo non
      costante il secondo canale (−0.0112 / +0.0192 contro i voxel) va rimisurato prima di correggere.
      Gli altri quattro: (a) convenzione σ_px, (b) anisotropia *F*_AP,
      (c) re-randomizzazione del carving, (d) tiling. (c) e (d) si quantificano a geometria fiduciale
      con semi diversi e si sottraggono in quadratura.
- [ ] **3.4 — La misura che conta:** ∂*D*/∂fiducia sul **deficit**. Riportare anche
      ∂*N*_H1/∂fiducia sui due lati: è il prodotto metodologico.
- [ ] **3.5 — Rango empirico per ogni punto**, statistica primaria.
- [ ] **3.6 — Erosione per punto**, *k* = 0–3, con **✧ *k* = 1 come livello di riferimento**.

---

## Fase 4 — Componente B, ri-perimetrata

### 4.1 — Cosa il Paper 1 ha già fatto (da **non** rifare)

*w*_FKP(*z*) dal random (peso medio in-maschera 0.309), voxelizzazione mock pesata, 60 realizzazioni
appaiate, **Δ*N*_H1 = −78.0 ± 8.0 (−9.7σ)**, −1.09% del deficit, verso i dati.

### 4.2 — Cosa resta

- [ ] **4.2a — Ensemble v2 completo** sui 2000. ~2 h/emisfero di cache + ~14 h di TDA.
      **✦ Priorità assoluta nella serie:** i Paper 3 e 4 ne hanno bisogno già corretto.
- [ ] **4.2b — Le predizioni a un punto, mai misurate.** Registrarle **prima**: varianza di δ
      mock/DESI da 1085 verso 1; curtosi in eccesso di ν da +3.90 verso +0.20; ν₉₉ − ν₁ da 5.6σ verso
      3.22σ; massimo δ da 32 244 verso ~125; **★ Box–Cox** 20.3% → 17.6% su v1, **deve comprimersi**
      su v2.
- [ ] **4.2c — Voxel patologici:** ~4000 per mock (1.3%) → ~0.
- [ ] **4.2d — Tab. 12 su v2 come cancello interno:** voxel multi-occupati e molteplicità massima
      **non dipendono dai pesi** e devono restare identici.

### 4.3 — Componente C: la tensione erosione ↔ FKP

- [ ] **4.3a** Erosione *k* = 0–3 sull'ensemble v2.
- [ ] **4.3b — Predizione dichiarata:** se l'attribuzione del Paper 1 §8.1 è corretta, su v2 il picco
      a *k* = 1 deve **appiattirsi**. Se resta, il massimo è **geometrico** (bordo del footprint).
- [ ] **4.3c** In entrambi i casi: risultato pubblicabile, sezione autonoma.

---

## ✦ Fase 4D — Componente D: risposta ai parametri cosmologici *(ex Paper 5)*

Il meccanismo viene prima dei numeri: `carve_cutsky` sottocampiona ogni mock a
`N_TARGET_BGS = 217614` seguendo l'*n*(*z*) di DESI. Il density matching **rimuove l'informazione di
ampiezza per costruzione**; sommato alla Prop. 1, l'insensibilità è prevedibile a priori.
*(217 614 coincide con l'`N_data` di NGC: il bersaglio è il campione DESI.)*

- [x] **D1 — Decomposizione della varianza.** Già in M26 R1 §5.5: σ_cos 261.5 (69.8%), σ_HOD 128.3
      (16.8%), σ_realizz. 114.6 (13.4%), σ_fixed 172.0, σ_tot 313.0.
- [x] **✦ D2 — Correlazioni parziali a *n* = 2000.** Eseguito, entrambi gli emisferi, con sentinella
      di join su Ω_m e identificazione delle colonne dai valori.

      | | NGC | SGC |
      |---|---|---|
      | *n*_s | **+0.3976** [0.3601, 0.4339] | **+0.4163** [0.3794, 0.4519] |
      | *h* | +0.2373 | +0.2201 |
      | σ₈ | +0.1897 | +0.2484 |
      | Ω_m | +0.1855 | +0.1667 |
      | Ω_b | −0.1387 | −0.1319 |
      | *M*_ν | −0.0673 (*p* = 0.033) | −0.0203 (*p* = 0.72) |
      | *w*₀ | +0.0549 (*p* = 0.013) | +0.0474 (*p* = 0.032) |

      *n*_s è il parametro guida a **7.4σ e 8.4σ** sopra la soglia dichiarata 0.25. L'ordinamento è
      coerente con la tesi della forma: *n*_s, *h*, Ω_m, Ω_b sono parametri di **forma** dello
      spettro. **I due emisferi non sono indipendenti** — stessa suite di 2000 simulazioni — quindi
      l'accordo è atteso per costruzione e non va presentato come conferma.
- [x] **✦ D3 — Predizione P1 SMENTITA, da registrare.** «|*r*(*w*₀)| < 0.05» fallisce in NGC per
      0.005. La soglia era mal calibrata: a *n* = 2000 l'errore su *r* è 0.0224, quindi chiedeva a un
      effetto nullo di stare entro 2.2σ, su sette parametri. **Con correzione di Bonferroni
      (*p* < 0.0071) nessun emisfero è significativo.** La conclusione non cambia e si rafforza:
      la pendenza è ora **misurata**, non limitata.
- [x] **✦ D4 — Il tetto di sensibilità, come misura.** Vincolo 1σ implicito su *w*₀: **±3.13** (NGC) e
      **±5.71** (SGC), contro ±0.06 di BAO DESI — **52× e 95× peggio**. È il numero che chiude la
      questione CPL e il prodotto citabile per chiunque proponga statistiche topologiche per
      vincolare la cosmologia.
- [x] **✦ D5 — Il tetto di *R*².** *R*²_max = (σ_cos/σ_tot)² = **0.698**. Osservato: **0.2606** (NGC)
      e **0.2773** (SGC), cioè il 37.3% e 39.7% del tetto. Non spiegato: il **62.7%** e **60.3% della
      varianza cosmologica**.
- [ ] **✦ D6 — Escludere la non linearità, PRIMA di rivendicare D5.** *R*² è lineare: una dipendenza
      quadratica o di interazione apparirebbe identica a «varianza non parametrizzata».
      `paper2_compD_nonlinear.py`, due test:
      - **quadratico + interazioni** (7 → 14 → 35 termini) con *R*² validato incrociato;
      - **regressione su *P*(*k*)** dal cache `results/phase7_pk_nwlh_cache.npz`, e regressione dei
        **residui** dei parametri su *P*(*k*).
      Lettura: se *P*(*k*) chiude il divario, *N*_H1 **è** una statistica del due punti e i sette
      parametri fallivano solo perché la mappa parametri → *P*(*k*) non è lineare; se non lo chiude,
      la parte non spiegata è **oltre il due punti**, e si collega al residuo beyond-two-point di
      1710 generatori del Paper 1. *Attenzione ai tetti: per predittori misurati sulla stessa
      realizzazione il tetto non è 0.698 ma (σ_cos²+σ_realizz.²)/σ_tot² = 0.832.*
- [ ] **✦ D7 — Invarianza monotona come pregio.** Riformulare la Prop. 1 anche come **garanzia di
      robustezza**: immunità per teorema agli errori di calibrazione dell'ampiezza, al bias di
      luminosità e a qualunque errore moltiplicativo nei pesi.
- [ ] **✦ D8 — Il confronto scatola/cut-sky con la sua riserva.** 15.3% contro 0.88%, fattore ~17.
      **Non attribuibile al density matching da solo**: volume, geometria, cella (7.81 contro 15.60),
      bordo e mascheratura differiscono. È un **limite superiore**, e va scritto così.

---

## Fase 5 — Analisi, budget di errore, interpretazione

- [ ] **5.1** Budget sistematico aggiornato: banda 17–29% del Paper 1, termine AP misurato, ±3.4%
      residuo di maschera, termine di tiling. Denominatori conservativi ovunque.
- [ ] **★ 5.2 — Tab. 8 del Paper 1, due righe.** *"fiducial cosmology / AP"* → bound numerico;
      *"box tiling"* → superata da M26 R1 §5.6, citare i numeri e non lo stato "open".
- [ ] **5.3 — Stabilità del residuo beyond-two-point** (1710.5 ± 40.6, 6.8σ, σ_Δ = 250.5) su v2.
      **✦ Va verificato per primo dentro 4.2a:** è l'unico rischio della serie che tocca un
      manoscritto già sottomesso. Aggiungere lo split a tre in persistenza di M26 R1 §5.2 (+1908
      near-diagonal, −9408 bulk, +332.5 coda) come cancello diagnostico.
- [ ] **✦ 5.4 — CINQUE "practice" per §6.2 di M26**, non tre:
      1. verificare w̄, **la frazione di voxel sotto soglia** e *d*_med per ogni geometria **e per
         regione**. La media da sola non intercetta la scalinata (w̄ = 0.9964 mentre il 17.8% dei
         voxel sta sotto 0.99), e una soglia scalare unica escluderebbe il fiduciale SGC;
      2. pesare i mock come i dati;
      3. **dichiarare la convenzione di σ_px** — unità fisiche o di griglia. Ampiezza: **1.64%**
         picco-picco lungo la linea *F*_AP dentro questa griglia, **40%** fra suite con celle di
         dimensione diversa;
      4. **✦ dichiarare il gauge** della decomposizione isotropo/anisotropo: il residuo varia di un
         fattore 4.3 con la scelta, e i minimi quadrati sovrastimano fino al 26.4%;
      5. **✦ dichiarare la convenzione di *F*_AP** — α_⊥/α_∥ o il reciproco — con la formula.
- [ ] **✦ 5.5 — Una predizione dichiarata e smentita, da riportare nel manoscritto.** «σ(realizzazione)
      domina, oltre l'80%» è stata smentita di **due ordini di grandezza**; la decomposizione le
      assegna il 13.4%. Più la P1 di D3. Il Paper 1 ha già stabilito il precedente riportando il
      fallimento dell'albero decisionale pre-registrato.
- [ ] **5.6** Se 4.3b lo richiede, nuova nota correttiva — sempre unica, mai a pezzi.

---

## Fase 6 — Record congelato e riproducibilità

- [ ] **6.1** JSONL append-only, atomico, crash-safe, resumable, per ogni run di Fase 3, 4 e 4D.
- [ ] **6.2** Ogni numero del manoscritto tracciabile a un singolo run verificato.
- [ ] **6.3** Tag `v2.1-paper2`; DOI Zenodo aggiornato.
- [ ] **6.4** `gate_preinvio.py` adattato al Paper 2, eseguito sul PDF finale.
- [ ] **6.5** Elenco esplicito dei risultati **ritirati** rispetto al canovaccio del 24 luglio.
- [ ] **✦ 6.6** Archiviare `canovaccio_paper5.md`: il contenuto vive nella Fase 4D.

---

## Fase 7 — Scrittura

**✦ Titolo di lavoro:** *"What does the loop count respond to? Geometry, weighting and cosmology in
persistent homology of voxelized redshift surveys"*

### Struttura

1. Introduzione: la domanda della funzione di risposta; le limitazioni (ix) e (ii).
2. **Teoria:** Prop. 2 e 2′, Lemma 3, il gauge di Chebyshev, posizionamento.
3. Il canale isotropo è una convenzione di griglia; le due convenzioni di σ_px a confronto sulla
   linea *F*_AP.
4. Il canale anisotropo: griglia (α_iso, *F*_AP), w̄ per punto, esclusioni, tiling, **test di
   completezza della parametrizzazione**.
5. Risposta AP del deficit: decomposizione a quattro contributi, ranghi empirici.
6. **✦ Risposta ai parametri cosmologici:** decomposizione della varianza, *w*₀ a *n* = 2000, *n*_s
   come parametro guida, il tetto di sensibilità, il tetto di *R*².
7. Ensemble v2 e le predizioni a un punto.
8. Erosione su v2 e risoluzione della tensione §7.2/§8.1.
9. Budget sistematico; Tab. 8 chiusa.
10. Discussione: **la funzione di risposta di *N*_H1**, cosa resta non testato, priorità per i
    Paper 3 e 4. **✧ Dichiarare esplicitamente quali limitazioni di M26 R1 restano aperte dopo il
    Paper 2** — ex 0.7b, migrata qui: la mappatura (i)–(xi) è chiusa, la dichiarazione è scrittura.

### Figure

- **✦ (F1)** *f*(*r*) − α_iso·*r* in voxel per geometria, banda **±0.1 voxel** (non ±1: il massimo
  reale è 0.57), con la soglia dell'artefatto di padding (0.013) come riferimento inferiore.
- **(F2)** Deficit contro *F*_AP a α_iso fissato, con σ_Δ come banda.
- **✦ (F3)** σ_px e w̄ per geometria, con le soglie **per regione**; punti esclusi in grigio.
- **(F4)** Illustrazione della Prop. 2: stesso campo, due dilatazioni, diagrammi identici.
- **(F5)** PDF di δ e ν, v1 contro v2 contro DESI.
- **(F6)** Erosione *k* = 0–3, v1 contro v2, due emisferi.
- **✦ (F7)** **La funzione di risposta:** |∂*N*_H1/∂θ| normalizzato per θ ∈ {σ₈, Ω_m, Ω_b, *h*,
  *n*_s, *M*_ν, *w*₀, α_iso, *F*_AP}, con le barre **zero-per-teorema** marcate diversamente dalle
  **zero-per-misura**. *È la figura che riassume il paper: senza la Componente D ha metà delle barre.*
- **★ (F8)** Molteplicità di tiling e frazione indipendente per geometria, col gradino evidenziato.
- **✦ (F9)** *R*² osservato contro il tetto 0.698, per emisfero, con la scomposizione lineare /
  quadratica / *P*(*k*) di D6.

---

## Rischi e mitigazioni

| rischio | probabilità | mitigazione |
|---|---|---|
| Esito nullo su A e D → paper percepito sottile | **alta** | **✦** È ciò che la fusione risolve: il nucleo positivo è la funzione di risposta, non i due nulli. F7 la rende visibile. |
| **✦ Il divario di *R*² è solo non linearità** | **media** | D6 lo esclude prima di rivendicarlo. |
| **✦ Convenzione σ_px sbagliata sulla linea B** | media | 1.4a la fissa prima dei run; 3.0 la applica. |
| Uno o più angoli falliscono w̄ | alta | 1.2c li esclude a priori. **✦** Se cadono C1 o C4, **dire** che il terzo canale resta non misurato. |
| **★** Il gradino di tiling simula una risposta AP | media | 3.2a–c. **✦** Il blocco B è immune per costruzione. |
| Ensemble v2 sposta il residuo beyond-two-point | bassa | 5.3, **per primo**. |
| Re-randomizzazione del carving domina il segnale | media | 2.5 + sottrazione in quadratura (3.3). |
| Il Paper 1 cambia in revisione | media | 0.2. |

---

## Ordine di esecuzione

```
[FATTO]  0.5 → 1.1 → 1.2a → 1.3 → 2.4 → D1/D2/D3/D4/D5
                                        ↓
        D6 (non linearità + P(k))  ‖  1.2b (w̄, d_med per regione)   [minuti/ore]
                                        ↓
                     1.2c → 1.3a → 1.5a → 1.4/1.4a
                                        ↓
          2.1 [FATTO] → 2.1-M [FATTO] → 2.1-D2 (runner)
                                        ↓
                    2.2a/2.2b → 2.3        [PUNTO DI DECISIONE]
                                        ↓
                          pre-registrazione 0.6
                                        ↓
         4.2a (ensemble v2, ~16 h)  ‖  3.0 → 3.1 (lato dati, 10 run)
                 ↓ 5.3 per primo
        4.2b/c/d + 4.3a/b              3.2 + 3.2a/b/c (mock appaiati)
                                        ↓
                       3.3 → 3.4 → 3.5 → 3.6
                                        ↓
                          Fase 5 → Fase 6 → Fase 7
```

**✦ Due cose sono cambiate nell'ordine.** La Componente D è quasi tutta **già eseguita** e sale in
cima; e **5.3 va dentro 4.2a**, non dopo, perché è l'unico controllo che tocca un manoscritto
sottomesso.

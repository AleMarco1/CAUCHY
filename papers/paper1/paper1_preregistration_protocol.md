# Pre-registration protocol — Paper 1 (v2)
## "What kind of field has fewer loops? Linking one-point structure and H1 topology in DESI BGS"

**Serie:** follow-up del deficit di generatori H1 in DESI BGS (paper base MN-26-2100-P).
**Pipeline:** CAUCHY v2.0. **Tag di release:** `CAUCHY-paper1-prereg-vX.Y` (da creare al deposito).
**Stato:** v2 — slot [C1] e [C2] CHIUSI; esperimento primario **ridisegnato** (§4) dopo il risultato di invarianza di §3bis.
**Data congelamento:** _____________  **DOI pre-reg:** _____________

---

## §0 — Input congelati (tutti verificati sui prodotti su disco)

### 0.1 Definizione della statistica — **attenzione: due quantità distinte**

Il codice CAUCHY usa il nome `beta1_max` per **due cose diverse** in fasi diverse. Il paper base usa la prima.

| Simbolo | Definizione operativa | Nel codice |
|---|---|---|
| **N_H1** (= "β1max" del paper base) | **numero totale di generatori H1** = cardinalità del diagramma di persistenza H1 (coppie finite, dopo rimozione delle feature che toccano la sentinella) | `phase8_cutsky_mocks.compute_tda_features` → `feats[4] = len(p1)`; commento esplicito `# feats[4] = beta1_max (n loops)` |
| **β1^peak** | **altezza del picco della curva di Betti** β1(ν) | `phase1_tda_baseline.extract_features` → `b1_peak_height` |

> **Il deficit del paper base è su N_H1, non sul picco della curva.** Conferma incrociata in `phase6_bgs_tda_features.json`, dove NGC riporta *entrambi*: `n_loops_beta1 = 29 683` e `b1_curve_max = 11 132`.
> La "discrepanza" 35 400 vs 10 570 era dunque apparente: 10 570 è β1^peak sul **box periodico pieno** (phase1, campo di materia Quijote), 35 467 è N_H1 sul **cut-sky mascherato** (phase8/9, campo di galassie). Statistiche diverse su campi diversi.

**Statistica primaria del Paper 1: N_H1** (per continuità col paper base). Secondaria, sempre riportata: β1^peak.

### 0.2 Catena di costruzione del campo (slot [C1] — CHIUSO)

Da `phase8_cutsky_mocks.build_field`, applicata **identica** a DESI e ai mock:

```
delta   = (n_d - alpha*n_r) / (alpha*n_r)        # delta FKP, voxel validi
delta[~mask] = 0
nu[mask]     = log(1 + clip(delta[mask], -1+1e-3, None))   # log sul delta GREZZO
nu           = gaussian_filter(nu, sigma=SIGMA_PX)          # smoothing DOPO il log
nu[~mask]    = 0
nu[mask]    -= nu[mask].mean()                              # mean-sub entro maschera
```

- **Smoothing:** R = 5 Mpc/h fisici; `SIGMA_PX = R / Δx`. NGC: Δx = 1997.4/128 = 15.605 → σ_px = 0.3204. Box Quijote (phase1): Δx = 1000/128 = 7.8125 → σ_px = 0.64. (R10 → σ_px 1.28, usato nel test di sensibilità.)
- **Filtrazione:** **supralivello** su ν, implementata passando `-ν` a `gudhi.CubicalComplex` (che è sottolivello).
- **Filtrazione mascherata (canonica, `masked=True`):** l'esterno è posto a `-1e6` in ν, cioè `+1e6` in `-ν`, così entra per ultimo; le feature con birth o death oltre `cutoff = 5e5` sono **scartate**. È l'unico trattamento like-for-like corretto per una survey limitata.
- **Soglie:** phase8/9 → 100 bin `linspace(P1, P99)` di ν **entro maschera**; phase1 (full box) → 50 bin `linspace(P5, P95)`.
- **Maschera nei campi salvati:** i voxel esterni portano un **valore-sentinella costante** = moda esatta del cubo (SGC: `0.013023147359490395`; da estrarre per campo). `mask = (campo != moda)`. SGC: 172 225 voxel interni (8.21%).
- **Contenuto dei file `bgs_*_delta_128.npy`:** δ **grezzo** (mean-subtracted entro maschera), **non** ν — coerente con il massimo osservato δ ≈ +152 e col commento nel codice ("delta up to +150 → log(151) = 5.0").

### 0.3 Record numerici congelati (slot [C2] — CHIUSO)

| Quantità | Valore | Fonte |
|---|---|---|
| N_H1 DESI **NGC** (masked) | **28 256** | `phase8_w0_exclusion`, `phase8_test2_masked`, `phase9_*` (concordi) |
| N_H1 mock cut-sky, baseline | **35 467.15** | `phase8_fiber_surrogate.baseline_mock_beta1_max` |
| **Deficit D (NGC)** | **≈ 7 100 – 7 211** (7 100.01 mask-robustness; 7 196.57 rsd-satellite; 7 200.93 growth) | `phase9_*` |
| N_H1 DESI **SGC** | **15 122** | `phase9_sgc_likeforlike` |
| N_H1 mock SGC | **18 693.60 ± 177.96** | idem |
| Deficit frazionario | SGC 0.191 vs NGC 0.20 | idem |
| β1^peak mock (full box, phase1) | 10 549.96 ± 120.05 a ν = −0.0972 | `phase1_fiducial_cache` |
| Sensibilità smoothing | Δβ1 = 44.2σ tra R5 e R10 | `phase1_gate_result` ("Concern 1") |

> I valori 35 400 / 7 169 del canovaccio erano **corretti**: si riferiscono a questa configurazione cut-sky mascherata.

### 0.4 Test di chiusura eseguito (riproducibilità indipendente)

Reimplementando §0.2 da zero e applicandola a `bgs_sgc_delta_128.npy`: **N_H1 = 15 110** contro il valore congelato **15 122** (scarto 0.08%, attribuibile al `SIGMA_PX` SGC non ancora pinnato — il boxsize SGC differisce da quello NGC). La pipeline è quindi riproducibile fuori dall'ambiente originale. **Da pinnare prima del deposito:** `BOXSIZE`/`SIGMA_PX` dell'SGC (in `phase9_sgc_likeforlike.py`, `sgc_geometry`).

---

## §1 — Domanda scientifica

Il paper base osserva che il deficit di generatori H1 coesiste con una struttura a un punto anomala (coda ad alta densità più pesante, meno potenza a piccola scala, varianza del gradiente più alta) e congettura (Sez. 6.1): *"ciò che spiega la struttura a un punto spiegherà la topologia"*. Questo paper trasforma la congettura in un test quantitativo.

---

## §2 — Statistiche a un punto (definizioni congelate)

Calcolate **solo entro maschera**, su δ e su ν:

1. **PDF / counts-in-cells** su binning fisso (100 bin sui percentili 1–99, come la filtrazione; più 200 bin fini per i momenti).
2. **Momenti 1–4:** media, varianza, skewness, curtosi in eccesso.
3. **Funzione di eccedenza** F̄(ν_k) per ogni soglia della griglia canonica.
4. Confronto like-for-like DESI vs mock riportato come **rango empirico**.

---

## §3bis — Lemma di invarianza (risultato preliminare, già dimostrato)

> **Lemma.** Per una filtrazione di supralivello su complesso cubico, l'intero diagramma di persistenza è determinato dall'**ordinamento** dei valori delle celle. Una trasformazione **monotona crescente** del campo preserva l'ordinamento, quindi preserva la filtrazione cella-per-cella. Ne segue che **N_H1 è esattamente invariante** sotto qualunque rimappatura monotona, e β1(ν) è invariante a meno di una riparametrizzazione dell'asse ν (quindi anche β1^peak è invariante).

**Verifica numerica (eseguita, SGC):** rimappando ν *post-smoothing* sui quantili di una gaussiana e di un'esponenziale, N_H1 resta **15 110 → 15 110 → 15 110**, invarianza esatta. Rimappando invece δ *pre-smoothing*: 15 110 → **14 869** (cambia).

**Conseguenze — due, entrambe centrali per il paper:**

1. **Il disegno originario dell'esperimento (rimappare il campo filtrato) è vacuo:** darebbe f_1p ≡ 0 per costruzione matematica, non per fisica. Va sostituito (§4).
2. **È esso stesso un risultato pubblicabile e forte:** poiché anche il log-transform è monotono, *nessuna* statistica a un punto del campo può, da sola, spiegare un deficit di N_H1. Qualunque spiegazione "one-point" deve agire **attraverso lo smoothing**, cioè attraverso l'interazione fra la distribuzione a un punto e il filtro spaziale a R = 5 Mpc/h. Questo restringe drasticamente lo spazio delle spiegazioni ammissibili e va enunciato come lemma nel paper.

---

## §4 — Esperimento primario (RIDISEGNATO): remapping pre-smoothing

**Principio:** la rimappatura agisce sul **δ grezzo**, prima di log e smoothing; poi si esegue la pipeline canonica §0.2 invariata. Così l'esperimento isola l'effetto della PDF a un punto *nel solo canale in cui può averne uno*.

**Algoritmo (deterministico):**

1. Sia `X` = valori δ del mock **entro maschera** (lunghezza M); `T` = valori δ di DESI entro maschera.
2. Ranghi di `X` con tie-break stabile per indice (`np.argsort(kind="stable")`); nessuna casualità.
3. Quantili bersaglio `Q = sort(T)`; rimappatura per interpolazione lineare (`np.interp`) sui quantili `(r+0.5)/M`.
4. Ricostruire il cubo δ' (interno = rimappato, esterno = fill), applicare **build_field** §0.2 e la **filtrazione mascherata**.
5. Registrare N_H1' , β1'(ν), β1'^peak per ogni mock.

**Parametri congelati:** bersaglio primario **DESI NGC**; secondari SGC e NGC+SGC (§9). **N mock = 2000** (costo misurato: ~15–25 s per filtrazione 128³ ⇒ ~10–14 h single-core, parallelizzabile); fallback pre-registrato a 500 (indici 0–499) se il runbook lo imponesse.

---

## §5 — Metrica primaria

- Deficit osservato: **D = N_H1^mock − N_H1^DESI** (NGC: 35 467.15 − 28 256 = **7 211.15**).
- Effetto: **Δ_remap = N_H1^mock − ⟨N_H1'⟩**.
- **Frazione spiegata: f_1p = Δ_remap / D.**

Incertezza: dispersione mock-to-mock di N_H1' e σ_null (§6) sommate in quadratura; intervallo empirico 16–84 percentile.

---

## §6 — Null test della procedura

Rimappare ogni mock sulla **PDF media dei mock** `T0` (quantili medi dei 2000). Attesa: f_null ≈ 0. σ_null = std di (N_H1' − N_H1) → pavimento di rumore, usato in §5 e §8. Se |f_null| non è compatibile con 0, la procedura è distorta e va corretta **prima** di interpretare §4.

> Nota: sotto il null il remapping resta *quasi* monotono ma non identico (le PDF differiscono), quindi f_null ≠ 0 esattamente; σ_null ne misura l'ampiezza tipica.

---

## §7 — Esperimento speculare

Rimappare δ di DESI (NGC) sulla PDF media dei mock e ricalcolare N_H1. Sotto H_1p pura: N_H1 risale verso 35 467. Metrica g_1p = (N_H1^DESI,remap − N_H1^DESI)/D. La coerenza f_1p ↔ g_1p è un check di falsificazione interno.

---

## §8 — Albero decisionale pre-registrato

Con η = 3·σ_null/D (fissato numericamente al congelamento):

| Condizione | Verdetto |
|---|---|
| f_1p ≥ 1 − max(0.2, η) **e** g_1p ≥ 1 − max(0.2, η) | **Deficit interamente one-point** (mediato dallo smoothing). La domanda si sposta su cosa genera quella PDF: bias non lineare, shot noise FKP, sistematici. |
| f_1p ≤ max(0.2, η) **e** g_1p ≤ max(0.2, η) | **Deficit di fase/connettività.** Nessuna statistica a un punto lo cattura → l'anomalia si rafforza. |
| altrimenti | **Deficit misto**; f_1p = quota one-point, con §3 a localizzare il residuo. |

Discordanza f_1p vs g_1p oltre 3σ → esito riportato come **instabile**, senza forzare una casella. Tutti gli esiti sono pubblicabili.

---

## §9 — Robustezza (pre-specificata)

1. **NGC vs SGC** (deficit frazionario già noto: 0.20 vs 0.191).
2. **Asse smoothing (Concern 1):** ripetere a R5 e R10 (σ_px 0.3204/0.64 e doppio). Domanda: **f_1p è stabile rispetto a R?** Dato il lemma §3bis, l'intero effetto one-point *vive* nello smoothing: la dipendenza da R è quindi una predizione qualitativa da testare, non un dettaglio.
3. **Scelta della PDF bersaglio:** NGC / SGC / combinata.
4. **Effetti di bordo:** erosione della maschera di 1 e 2 voxel (confrontabile con `phase9_mask_robustness`, che riporta swing del deficit fino a ~2 784 loop — da citare come contesto).
5. **Statistica secondaria:** ripetere tutto su β1^peak.

---

## §10 — Condizioni di stop

- |f_null| ≫ 0 in §6 → fermare, diagnosticare, ri-registrare.
- La reimplementazione non riproduce N_H1 dei record congelati entro ~0.5% su un campione di controllo → fermare e riconciliare (attualmente: 0.08% su SGC, dopo il pinning di σ_px SGC atteso migliore).
- Nessun risultato ritoccato dopo il congelamento; scoperte non previste in sezione "esplorativo" separata.

---

## §11 — Deliverable

- **Record JSON congelati** per esperimento, con SHA dei campi in input.
- **Figure:** (F1) PDF δ e ν, DESI vs mock; (F2) β1(ν) con banda; (F3) scatter N_H1 pre/post remapping sui 2000 mock; (F4) deficit per soglia; (F5) f_1p vs R (smoothing); (F6) illustrazione del lemma di invarianza.
- **Repository** con tag per paper; riproducibilità bit-per-bit.
- **DOI della pre-registrazione citato nel manoscritto** (neutralizza il residuo look-elsewhere, Sez. 5.6 del paper base).

---

## §12 — Politica di deviazione

Ogni scostamento successivo al deposito va in un changelog datato con motivazione, riportando il risultato sia con protocollo originale sia con la variante, marcato "post-registrazione".

---

### Checklist di deposito
- [x] [C1] definizione ν / smoothing / filtrazione pinnata (`phase8_cutsky_mocks.build_field`, `compute_tda_features`)
- [x] [C2] N_H1 DESI NGC/SGC, baseline mock, D
- [x] Statistica primaria disambiguata (N_H1 vs β1^peak)
- [x] Lemma di invarianza dimostrato e verificato numericamente
- [x] Esperimento primario ridisegnato su δ pre-smoothing
- [ ] `SIGMA_PX` / boxsize SGC pinnati
- [ ] Runbook tempo/RAM su 2000 mock (stima corrente ~15–25 s/campo)
- [ ] Tag repo creato, documento depositato, DOI inserito

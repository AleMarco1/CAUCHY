# Paper 1 — Record numerico congelato (v5 — COMPLETO)

**Pipeline:** CAUCHY v2.0 + `paper1_remap.py` v3, `paper1_null_mockmock.py`, `paper1_mask_erosion.py`, `paper1_mirror_likeforlike.py`, `paper1_step6_onepoint_betti.py` v2, `paper1_fkp_asymmetry.py`
**Statistica primaria:** N_H1 = numero di generatori H1 (`feats[4]`, "beta1_max" nel codice CAUCHY)
**Ultimo aggiornamento:** 25 luglio 2026 — sostituisce la v4. **Esperimento SGC concluso: tutti i claim centrali verificati in due emisferi.**

> **Cambiamenti rispetto alla v3.** Le statistiche a un punto sono state ricalcolate su **voxel puliti** (restrizione `field_r > P10`) in entrambi gli emisferi. Tre conseguenze: la distanza fra PDF scende da 18× a **5–10×**; la leptocurtosi dei mock si rivela **reale** e non artefatto; e la skewness passa da inutilizzabile a utilizzabile, con i due emisferi che **concordano solo dopo la pulizia**. Aggiunte le scale respinte a 2000 mock (materiale d'appendice).

---

## 0. Geometrie congelate

| | NGC | SGC |
|---|---|---|
| box (Mpc/h) | 1997.363 | 1904.5 |
| cella (Mpc/h) | 15.604 | 14.879 |
| σ_px canonico (R = 5 Mpc/h) | 0.32042 | 0.33606 |
| voxel in maschera | 307 805 (14.677%) | 172 225 (8.212%) |
| profondità mediana del footprint | 3.00 voxel | 2.83 voxel |
| galassie | ~217 000 | 82 429 |

## 1. Test di chiusura

| Verifica | Esito |
|---|---|
| `build_field` ricostruita vs modulo | identica, max\|diff\| = 0.000e+00 |
| `compute_tda_full` vs `compute_tda_features` | identica, max\|diff\| = 0.0 |
| `voxelize_mock` ricostruita vs sorgente | identica riga per riga |
| **N_H1(DESI NGC)** | 28 256 vs 28 256 — **0.000%** |
| **N_H1(DESI SGC)** | 15 122 vs 15 122 — **0.000%** |
| **N_H1 mock SGC** | 18 693.595 vs 18 693.60 — **esatto** |

## 2. Lemma di invarianza monotona

> Per una filtrazione di **supralivello** su complesso cubico il diagramma di persistenza è determinato dal solo **ordinamento** dei valori delle celle. Ogni trasformazione **monotona crescente** lascia N_H1 esattamente invariato.

Verifica: 15 110 → 15 110 → 15 110 (PDF gaussiana ed esponenziale). Rimappando δ pre-smoothing: 15 110 → 14 869.

**Corollari.** (a) Nessuna statistica a un punto può spiegare un deficit di N_H1 se non attraverso lo smoothing. (b) Il deficit del paper base non può essere l'artefatto di alcuna riscalatura monotona.

| σ_px | R (Mpc/h) | peso del voxel centrale |
|---|---|---|
| **0.3204** | **5** | **95.54%** |
| 0.6408 | 10 | 24.18% |
| 1.2817 | 20 | 3.03% |
| 1.9225 | 30 | 0.79% |

---

## 3. Risultato principale — R = 5 Mpc/h, due emisferi

| | NGC (2000 mock) | SGC (2000 mock) |
|---|---|---|
| DESI N_H1 | 28 256 | 15 122 |
| mock N_H1 | 35 436.7 ± 313.0 | 18 713.0 ± 197.8 |
| **D** | **+7 180.7** | **+3 591.0** |
| **D/base** | **20.26%** | **19.19%** |
| **z** | **−22.94** | **−18.16** |
| **f_1p** | **−0.01421 ± 0.00014** | **−0.04075 ± 0.00025** |
| **g_1p** | −0.1439 | −0.2428 |
| risposta one-point | +0.29% (opposto al deficit) | +0.78% (opposto al deficit) |
| b1_peak deficit | 36.91% | 37.15% |
| verdetto §8 | PHASE_CONNECTIVITY | PHASE_CONNECTIVITY |
| null (f_null) | imparziale | imparziale (−0.0024, σ_null 32.2) |

**Entrambi gli emisferi: deficit ~20%, canale one-point chiuso, verdetto di fase.** f_1p differisce di ~3× fra i due (−0.014 vs −0.041), entrambi minuscoli e di verso opposto al deficit — coerente con l'asimmetria di sensibilità (l'accoppiamento one-point/topologia dipende dal campo).

### Il deficit non è di natura a un punto (NGC)

| | valore |
|---|---|
| distanza PDF DESI vs mock (KS, **voxel puliti**) | **6.8×** la dispersione mock-to-mock |
| risposta topologica al remapping | **+102.0 loop = +0.29%**, verso opposto al deficit |
| f_1p | **−0.014206 ± 0.000141** |
| g_1p (speculare like-for-like, 50 bersagli) | **−0.1439 ± 0.0014** |
| deficit corretto, avanti | 7 282.7 = 20.49% |
| deficit corretto, speculare lfl | 8 213.9 = 23.18% |

Le tre stime a R5 concordano: grezzo 20.26%, corretto avanti 20.49%, corretto speculare 23.18%.

### Asimmetria di sensibilità (risultato fisico)

| | risposta al remapping |
|---|---|
| mock che adottano la PDF di DESI | +0.29% |
| DESI che adotta la PDF dei mock | **−3.66%** |

**DESI è 12.7× più sensibile alla rimappatura a un punto dei mock.** L'accoppiamento struttura-a-un-punto ↔ topologia dipende dalla struttura di fase su cui la PDF viene imposta. Spiegazione fisica — non metodologica — della discordanza avanti/speculare (ipotesi dell'asimmetria del bersaglio: **falsificata**, il like-for-like dà 14.87% contro 14.67%).

### Null test

| variante | N | spostamento medio | esito | σ_null |
|---|---|---|---|---|
| scala media (§6 pre-registrato) | 2000 | −4.54 ± 1.07 loop | 4.2σ — **bias reale** | 47.82 |
| **mock→mock (§12 post-reg.)** | 200 | **−0.88 ± 2.14 loop** | 0.41σ — **imparziale** | 30.29 |

Bias sempre ≤ 4.5% dell'effetto one-point a ogni scala.

---

## 4. Erosione della maschera — solo R5 sopravvive

Criterio corretto: **stabilità della magnitudine**, non del segno (il verdetto `sign_stability` dello script è troppo indulgente e va sostituito).

| reg | R | w(er0) | D% er0 | er2 | er3 | escursione | ritenzione DESI/mock |
|---|---|---|---|---|---|---|---|
| NGC | **5** | 0.9980 | +20.23 | +20.59 | +18.62 | **2.0 pp** | **0.996** |
| SGC | **5** | 0.9964 | +19.11 | +19.99 | +17.27 | **2.7 pp** | **0.989** |
| NGC | 10 | 0.9587 | +18.87 | +32.01 | +22.54 | 13.1 pp | 0.838 |
| SGC | 10 | 0.9489 | +8.69 | +29.16 | +17.88 | 20.5 pp | 0.776 |
| NGC | 12 | 0.9483 | +13.00 | +37.01 | +23.33 | 24.0 pp | 0.724 |
| NGC | 15 | 0.9351 | +3.74 | +47.35 | +28.25 | 43.6 pp | 0.547 |
| SGC | 15 | 0.9215 | −9.22 | +45.27 | +26.16 | 54.5 pp | 0.501 |
| NGC | 17 | 0.9271 | −2.03 | +53.46 | +33.82 | 55.5 pp | 0.456 |
| NGC | 20 | 0.9157 | −6.71 | +62.11 | +46.04 | 68.8 pp | 0.355 |
| SGC | 20 | 0.8988 | −22.78 | +60.64 | +47.30 | 83.4 pp | 0.321 |
| NGC | 30 | 0.8817 | −12.68 | +76.38 | +79.05 | 91.7 pp | 0.210 |

### Criterio metodologico (risultato trasferibile)

> **L'omologia persistente su survey mascherata è affidabile solo se w ≳ 0.99**, con w = frazione media del peso del kernel gaussiano proveniente da dentro la maschera.

NGC e SGC collassano sulla **stessa curva** ritenzione–w pur avendo footprint, celle e σ_px diversi. Regola pratica: **σ_px ≲ profondità mediana del footprint / 9**. Per l'NGC dà σ_px ≲ 0.33 contro il canonico 0.3204 — la configurazione del paper base sta appena dentro il limite.

---

## 5. Asimmetria di pesatura FKP (limitazione documentata)

| ingrediente | peso |
|---|---|
| dati DESI | `WEIGHT * WEIGHT_FKP` |
| random DESI | `WEIGHT_FKP` |
| **mock (`voxelize_mock`)** | **`np.ones(...)`** |

`build_field` è identico sui due lati; l'asimmetria è a monte. Per DESI il peso FKP si cancella fra numeratore e denominatore di δ, per i mock no.

### Localizzazione (NGC)

| taglio su field_r | n voxel | entro 2 voxel dal bordo |
|---|---|---|
| P1 (0.0399) | 3 079 | **99.4%** |
| P5 (0.2575) | 15 391 | 98.1% |
| P10 (1.069) | 30 781 | 95.7% |
| *tutti i voxel in maschera* | 307 805 | *31.9%* |

Ogni mock ha ~**4 000 voxel (1.3%)** con δ oltre il massimo di DESI (125), `field_r` mediano **0.052** contro 16.42 globale (fattore 315), distanza mediana dal bordo **1 voxel**. Massimo osservato δ = 32 244.

### Effetto sulla topologia: nessuno

| taglio | voxel | DESI ritenzione | mock ritenzione | D/base | z |
|---|---|---|---|---|---|
| 0% | 100% | 100.0% | 100.0% | 20.26% | −26.66 |
| 1% | 99% | 98.4% | 100.1% | 21.63% | −27.22 |
| 5% | 95% | 93.5% | 100.1% | 25.53% | −25.28 |
| 10% | 90% | 88.4% | **98.7%** | 28.54% | −23.68 |

**I mock conservano il 98.7% dei loop eliminando il 10% dei voxel.** Spiegazione topologica: un voxel isolato a valore estremo genera una **componente connessa (H0)**, non un ciclo (H1).

### Banda sistematica del deficit

| trattamento del bordo | D/base | z |
|---|---|---|
| nessuno (fiduciale) | 20.3% | −25.4 |
| erosione 2 / 3 voxel | 20.6% / 18.6% | −18.9 / −16.6 |
| taglio field_r 1 / 5 / 10% | 21.6 / 25.5 / 28.5% | −27.2 / −25.3 / −23.7 |

**Da riportare come: deficit ≈ 20%, banda sistematica 18–29% secondo il trattamento del bordo, significatività fra −17 e −27 in ogni caso.**

---

## 6. Statistiche a un punto — **su voxel puliti** (`field_r > P10`)

> **Prescrizione.** Le statistiche a un punto sul footprint pieno sono contaminate dall'artefatto FKP e vanno scartate. La giustificazione empirica è nella §6.3.

### 6.1 Momenti di ν — i quattro utilizzabili

| | NGC DESI | NGC mock | z | rango | SGC DESI | SGC mock | z | rango |
|---|---|---|---|---|---|---|---|---|
| varianza | +5.626 | +2.636 | **+6.15** | 198/200 | +7.273 | +4.442 | **+6.40** | 200/200 |
| skewness | −1.258 | −1.628 | **+5.57** | 198/200 | −0.895 | −1.301 | **+5.82** | 200/200 |
| curtosi | +0.590 | +4.424 | **−5.06** | 1/200 | −0.557 | +1.837 | **−5.61** | 0/200 |
| mediana | +1.097 | +0.098 | **+13.82** | 200/200 | +1.320 | +0.276 | **+16.11** | 200/200 |

**I due emisferi concordano su tutti e quattro i momenti entro il 15% in z.**

Interpretazione: DESI ha varianza maggiore, mediana molto più alta (a media nulla per costruzione), è **meno** negativamente asimmetrico e **meno** leptocurtico dei mock.

### 6.2 Statistiche NON utilizzabili

| | z su footprint pieno → er2 → P5 → P10 |
|---|---|
| p99 NGC | −18.45 → +6.54 → −2.69 → +4.33 |
| p99 SGC | −20.89 → +5.89 → −4.69 → +3.09 |
| max NGC | −4.71 → −5.47 → −1.10 → **+1.22** (rango 182/200) |
| max SGC | −6.12 → −7.11 → −2.34 → **+0.22** (rango 134/200) |

Le statistiche di coda invertono il segno con la restrizione. Il `max` diventa **pienamente compatibile** su voxel puliti: l'intera "anomalia di coda" era l'artefatto FKP.

### 6.3 Giustificazione empirica della prescrizione

> Sul **footprint pieno** i due emisferi **discordano**: skewness z = −7.91 (NGC) contro +0.74 (SGC), segni opposti.
> Su **voxel puliti** concordano: +5.57 e +5.82.

La pulizia non "migliora" i numeri, li rende **coerenti fra emisferi indipendenti**. È l'argomento più forte a favore della prescrizione, più della motivazione teorica da sola.

### 6.4 Contaminazione in δ e in ν

| restrizione | var mock/DESI in δ (NGC) | (SGC) | in ν (NGC) | (SGC) |
|---|---|---|---|---|
| footprint pieno | 1000.6× | 2068.3× | 0.61 | 0.76 |
| erosione 2 | 58.3× | 296.8× | 0.50 | 0.63 |
| field_r > P5 | 26.2× | 60.7× | 0.51 | 0.66 |
| field_r > P10 | 3.7× | 8.1× | 0.47 | 0.61 |

In **δ** la contaminazione è devastante e peggiore nell'SGC (footprint più sottile), coerente con l'origine geometrica. In **ν** è contenuta: il log-transform funziona dove conta.

### 6.5 Distanze fra PDF

| restrizione | KS ratio NGC | KS ratio SGC |
|---|---|---|
| footprint pieno | 18.48× | 17.11× |
| erosione 2 | 5.20× | 7.38× |
| field_r > P5 | 7.87× | 10.16× |
| **field_r > P10** | **6.80×** | **8.13×** |

**Valore da citare: 5–10×** su voxel puliti. Il 18× della v3 era contaminato.

### 6.6 Dove mancano i loop

Confronto **puramente di fase** (mock rimappati sulla PDF di DESI), R5:

| ν (NGC) | DESI | mock | z |
|---|---|---|---|
| −1.50 | 1 231 | 2 083 | −4.3 |
| **−0.04** | **3 119** | **7 162** | **−22.1** |
| +0.69 | 5 896 | 12 208 | −14.0 |
| +1.41 | 8 450 | 11 275 | −6.9 |

I loop mancano attorno alla **densità media**, con z < −3 sul 55% della griglia. Non nei vuoti profondi né nei nodi densi: nel regime intermedio, filamentare.

SGC (139 mock parziali): deficit massimo **z = −21.2** a ν = −0.368. I due emisferi concordano sulla profondità del deficit di fase.

> Il confronto **senza** remapping è fuorviante: a ν fisso mescola "PDF diversa" con "topologia diversa" (dà z = +7 a ν negativo e z = −16 a ν alto). Solo il confronto a PDF appaiata è interpretabile.

### 6.7 `peak_nu` non è robusto a R ≥ 12

A R12 la curva β1 normalizzata di DESI ha **nove massimi locali sopra l'80% del picco** (t da 0.21 a 0.77, valori 975–906): è piatta, e l'argmax scivola. Il `peak_nu` dei mock resta stabile (−0.057 → −0.092). Usare `b1_peak` (altezza), non `peak_nu` (posizione).

---

## 7. Scale respinte — materiale d'appendice (2000 mock)

| R | σ_px | DESI | mock | D | D/base | f_1p | σ_null | verdetto |
|---|---|---|---|---|---|---|---|---|
| 10 | 0.6408 | 12 128 | 14 967.5 | +2 839.5 | +18.97% | −0.371 | 74.00 | respinta |
| 12 | 0.7690 | 9 443 | 10 863.4 | +1 420.4 | +13.08% | −1.102 | 33.51 | respinta |
| 15 | 0.9613 | 7 152 | 7 435.7 | +283.7 | +3.81% | −6.329 | 69.51 | respinta |
| 17 | 1.0894 | 6 149 | 6 031.9 | −117.1 | −1.94% | +15.908 | 92.15 | respinta |
| 20 | 1.2817 | 4 994 | 4 679.8 | −314.2 | −6.71% | +6.031 | 114.23 | respinta |
| 30 | 1.9225 | 3 352 | 2 973.6 | −378.4 | −12.72% | +4.564 | 131.28 | respinta |

Il confronto 500 vs 2000 mock su R12/R15/R17 sposta i valori dello 0.1–1%: **500 erano statisticamente sufficienti**, il beneficio del run completo è solo la confrontabilità della colonna σ_null.

**Il polo di f_1p.** f_1p = (base − remap)/D ha numeratore sempre negativo e denominatore che cambia segno: i valori |f_1p| > 1 sono divergenze, non frazioni. L'albero decisionale §8 assume D > 0 e f_1p ∈ [0,1] e va dichiarato non applicabile quando |D| non è ≫ della dispersione mock.

*Dettaglio non spiegato:* σ_null a R12 (33.5) resta anomalmente basso rispetto a R10 (74.0) e R15 (69.5) anche a 2000 mock, quindi non è effetto di campionamento.

---

## 8. Risultati ritirati

| | motivo |
|---|---|
| Inversione di segno del deficit a R ≥ 17 | erosione: contaminazione di bordo |
| Crossover a 16.3 Mpc/h | dipende da scale respinte |
| Deficit corretto scale-invariante 23.69% ± 2.60% | media su scale respinte |
| Tutte le scale R ≥ 10 | escursione 13–92 pp sotto erosione |
| Distanza PDF 18.2× | contaminata; il valore pulito è 5–10× |

### Errori di analisi, corretti in corso d'opera

- Test di chiusura SGC allo 0.08%: confrontava il campo phase6 con la pipeline phase9 — oggetti diversi. Il valore vero è 0.000%.
- Test sui surrogati che dava l'effetto di bordo come "modo comune": usava la stessa fase per i due campi, quindi cieco all'asimmetria decisiva.
- Ipotesi che la discordanza avanti/speculare fosse asimmetria del bersaglio: **falsificata**.
- Previsione che le metriche robuste riducessero il rapporto 8.1×: **falsificata**, lo aumentano (su footprint pieno).
- Ipotesi che la leptocurtosi dei mock fosse l'artefatto FKP: **falsificata**, sopravvive alla pulizia in entrambi gli emisferi.
- Criterio `sign_stability` nello script di erosione: troppo indulgente.
- Prescrizione iniziale "escludere la skewness": **rivista**, è utilizzabile su voxel puliti e lì i due emisferi concordano.

---

## 9. Stato dei lavori

| | stato |
|---|---|
| Esperimento primario NGC R5, 2000 mock | ✅ |
| Null mock→mock, speculare like-for-like | ✅ |
| Erosione NGC (7 scale) e SGC (4 scale) | ✅ |
| Diagnostico FKP NGC | ✅ |
| Step 6 NGC e SGC, one-point su voxel puliti | ✅ |
| Scale respinte a 2000 mock | ✅ (appendice) |
| Esperimento SGC R5, 2000 mock | ✅ PHASE_CONNECTIVITY, f_1p = −0.041 |
| Step 6 SGC, curve complete | 🔄 opzionale (one-point già fatto) |
| Emenda formale al protocollo §8 | ⬜ |
| **Tutti i claim centrali** | ✅ **completi, due emisferi** |
| Scrittura | ⬜ pronta a partire |

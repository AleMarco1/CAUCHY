# Risoluzione della discrepanza di dispersione 313 vs 445

**Record congelato** — Paper 1, revisione MNRAS, punto E2 della lettera dell'editore
e obiezione principale del Referee 2.

Stato: **chiuso**. Catena causale dimostrata, non inferita.

---

## 1. La contestazione

Il Referee 2 osserva che il manoscritto dichiara di usare l'ensemble congelato di
M26 e di riprodurne la media allo 0.1%, ma riporta una dispersione NGC di
**313.0** contro i **445** di M26. Legge la differenza come una riduzione del 30%
che gonfia meccanicamente la significatività, e ne conclude che nessun numero con
σ al denominatore è difendibile finché non è spiegata.

L'editore recepisce l'obiezione come punto bloccante E2.

## 2. Esito

**313.0 è il valore congelato. 445 è l'artefatto.** La direzione dell'errore è
opposta a quella supposta dal referee: Paper 1 non ha ristretto nulla, ha usato il
numero corretto. È M26 ad aver pubblicato una dispersione contaminata.

## 3. Catena causale

### 3.1 Il record autorevole

`results/phase8_test2_masked.json`, generato **2026-07-03T01:21:16Z**,
`n_mock_valid: 2000`, `masked_filtration: true`:

```
mock_beta1_max:  mean 35436.686
                 std  312.9891651683112
                 z_desi -22.94228298969569
                 rank_desi 0.0
n_floor_note: "N=2000; empirical p-floor ~1/2001. Ranks primary."
```

La catena di Paper 1 (`paper1_remap.py` → `results/paper1/per_mock_NGC_R5.jsonl`)
riproduce questi valori **cifra per cifra**, indipendentemente.

### 3.2 L'origine del 445

`results/phase9_likeforlike_arrays.npz` (chiave `beta1_max`): 35424.784 ± 444.814.
Non è l'ensemble congelato: è una **ricomputazione**, prodotta da
`phase9_extract_features.py` perché la tabella per-mock del run definitivo copriva
solo il pilota N=200 mentre l'istogramma empirico serviva sui 2000 grezzi.

### 3.3 I cubi del pilota, mai sovrascritti

`results/phase8_test2_fields/` conserva per gli indici **0–199** i cubi del run
pilota. `phase9_extract_features.py` esegue `glob("test2_*.npz")` su tutti i 2000 e
li tratta come l'ensemble definitivo.

Prova (`paper1_rev_v2h_monotone.py`, Spearman fra i due cache dentro maschera,
307 805 voxel, 300 000 campionati):

| indici | zona | Spearman |
|---|---|---|
| 200, 500, 1000, 1805 | controllo | 0.99957 – 0.99964 |
| 0, 16, 27, 105, 139, 189 | blocco | 0.597 – 0.673 |

Il confronto va fatto per **ranghi e dentro maschera**: N_H1 dai sottolivelli del
complesso cubico è invariante per rimappatura monotona, quindi un confronto
`max|a−b|` sul cubo intero è cieco alla domanda. I due cache tengono la stessa
informazione in scale diverse (Pearson ≈ 0.35 con Spearman ≈ 0.9996: relazione
monotona fortemente non lineare).

### 3.4 Prova diretta

`results/phase8_test2_permock.csv` contiene `beta1_max` del pilota per gli indici
0–199 (`paper1_rev_v2i_close.py`):

| confronto | uguali | correlazione |
|---|---|---|
| CSV pilota ≡ npz | **200/200** | 0.9999999999999998 |
| CSV pilota ≡ Paper 1 | **0/200** | 0.536 |

I primi 200 valori dell'npz **sono** i valori del pilota.

### 3.5 Perché nessuno se n'è accorto

`phase9_extract_features.py`, righe 149–156, confronta la media col valore
congelato e mai la deviazione standard:

```
drift = |35424.784 − 35436.7| / 313.0 = 0.0381   <   0.5   →   [ok]
```

Una σ passata da 312.99 a 444.81 (**+42%**) è stata stampata accanto al proprio
valore di riferimento e l'esito registrato è stato `consistent with frozen run`.

## 4. Perimetro della correzione in M26 (`cauchy_mnras.tex`)

Produttore dell'array contaminato: `phase9_extract_features.py`.
Consumatori: `phase9_empirical_histograms.py`, `phase9_replot_beta1max.py`,
`phase9_w0_response_curve.py`, `phase9b_majors.py`.

| voce | pubblicato | corretto |
|---|---|---|
| σ ensemble NGC (tabella battery, righe 459/510/636) | 445 | **312.99** |
| frazione stocastica della varianza (riga 735) | 6.1% | **12.4%** |
| r(β₁ᵐᵃˣ, Ωm) | +0.45 | **+0.150**  IC95 [+0.012, +0.283] |
| r(β₁ᵐᵃˣ, σ₈) | +0.29 | **+0.137**  IC95 [−0.002, +0.270] |
| r(β₁ᵐᵃˣ, w0) | −0.03 | **+0.011**  IC95 [−0.128, +0.150] |

Le correlazioni pubblicate sono riprodotte **esattamente** dall'array contaminato
(+0.4529, +0.2884, −0.0277): sono state calcolate su quei 200 indici, che sono
precisamente i cubi del pilota. Con i valori corretti, Ωm resta marginale (2.1σ) e
σ₈ diventa compatibile con zero.

### 4.1 Un problema di inferenza indipendente dall'errore numerico

Riga 735 conclude che «il restante ~94% è cosmologico, guidato da Ωm». Già con i
numeri pubblicati l'inferenza non regge: r = +0.45 implica r² = 20%, non 94%. Il
94% è un **residuo**, non un'attribuzione misurata.

Con i numeri corretti: stocastico 12.4%; i tre parametri cosmologici, all'incirca
indipendenti per costruzione nel Latin hypercube, ne spiegano insieme ~4%. Restano
**oltre l'80% non attribuiti** né all'HOD né ai parametri.

Spiegazione naturale: il test a 50 semi fissava sia la cosmologia sia la
realizzazione delle condizioni iniziali (indice nwLH 1805) e variava solo HOD e
downsampling. **La dispersione fra realizzazioni a cosmologia fissa non è mai stata
misurata.** È quasi certamente lì che sta il grosso della varianza.

Se confermato, la correzione **rafforza** l'argomento centrale: se la varianza
dell'ensemble è dominata dalla varianza cosmica di realizzazione e non dalla
dipendenza dai parametri, attribuire il deficit osservato alla cosmologia diventa
più difficile, non meno.

## 5. La conclusione primaria non si muove

Invariante rispetto a ogni trattamento provato (ensemble completo, esclusi i
patologici, esclusi i discrepanti, esclusi entrambi):

- mock sotto DESI: **0** in entrambi gli emisferi
- rank: **1/2001**, al p-floor empirico
- margine sotto il minimo assoluto dell'ensemble: **+2970** generatori (NGC),
  **+1100** (SGC)

L'intera indagine riguarda il **denominatore delle z**, non la conclusione. È
esattamente la ragione per cui l'editore ha ragione a chiedere la statistica basata
sui ranghi — e per cui `"Ranks primary"` era già scritto nel record congelato del
3 luglio, prima di qualunque rapporto dei referee.

## 6. Bozza per la response letter (punto E2)

> The referee is right that the two dispersions cannot both be correct, and we
> thank them for forcing the issue: tracing it uncovered an error, though not the
> one anticipated.
>
> The frozen Phase 8 record (`phase8_test2_masked.json`, 2026-07-03, N=2000,
> masked filtration) reports σ = 312.989 for the NGC ensemble, together with
> mean 35436.686 and z = −22.942. The present work reproduces these values
> digit-for-digit through an independent chain. The value σ = 445 quoted in M26
> does not come from that frozen record: it comes from a later recomputation
> which, for mock indices 0–199, read cached field cubes left over from the N=200
> pilot run rather than those of the definitive run. We verified this directly:
> the pilot per-mock table matches that recomputation on 200 of 200 entries and
> the definitive chain on none of them.
>
> The recomputation carried a consistency check against the frozen record, but the
> check compared means only and never dispersions, so a 42% inflation of σ passed
> undetected.
>
> We therefore report σ = 312.989 as the correct dispersion and are submitting a
> corrigendum to M26, which affects its Table 3, the variance decomposition in
> Section 5.3, and the reported β₁ᵐᵃˣ–cosmology correlations.
>
> We stress that none of this affects the primary result. No mock in either
> hemisphere falls below the data under any treatment of the ensemble; the rank
> statistic sits at the empirical floor of 1/2001 throughout, and the data lie
> 2970 (NGC) and 1100 (SGC) generators below the most extreme mock in the suite.
> Following the Editor's point E2 we have moved the rank statistic to the
> abstract and demoted the Gaussian-equivalent z to a parenthetical, as the frozen
> record itself had already designated ("Ranks primary").

## 7. Punti aperti

1. **SGC non verificato allo stesso modo.** Il confronto col pilota è stato fatto
   solo su NGC: l'npz contiene `beta1_max` solo per quell'emisfero. Va accertato se
   `phase9_sgc_likeforlike.py` presenti la stessa contaminazione, e se il record
   congelato SGC sia coerente coi nostri valori.
2. **Dispersione fra realizzazioni a cosmologia fissa.** Mai misurata. Serve per
   rifare la decomposizione della varianza di §4.1 in modo difendibile.
3. **Rigenerazione dei 200 cubi.** Non necessaria per Paper 1 (la nostra catena ha
   già i valori corretti per tutti i 2000), ma serve per rifare i prodotti a valle
   di M26 — istogramma empirico e curva di risposta a w0.
4. **Comunicazione all'editore.** La correzione tocca un manoscritto ancora in
   review. Va segnalata esplicitamente e in modo tempestivo, non lasciata emergere
   solo dalla revisione di Paper 1.

## 8. Tracciabilità

| script | esito |
|---|---|
| `paper1_rev_v2v3.py` | rank empirici; individuato l'npz; 1800/2000 valori identici |
| `paper1_rev_v2b_outliers.py` | σ_px costante; discrepanti = esattamente 0–199; σ robuste ~uguali |
| `paper1_rev_v2c_provenance.py` | cosmologia definita solo su 0–199 |
| `paper1_rev_v2d_exchange.py` | blocco anomalo solo in M26, in N_H1 e in mean_pers1 |
| `paper1_rev_v2e_suite.py` | test di scambiabilità corretto; correlazioni con IC |
| `paper1_rev_v2f_srcdump.py` | identificato il produttore dell'npz |
| `paper1_rev_v2g_frozen.py` | letto il record congelato |
| `paper1_rev_v2h_monotone.py` | confronto per ranghi dentro maschera |
| `paper1_rev_v2i_close.py` | prova diretta col CSV del pilota; numeri corretti |

Report JSON corrispondenti in `results/paper1/rev_*.json`.

### Errori commessi durante l'indagine, e corretti

- Test di provenienza basato su timestamp: privo di valore diagnostico (vero per
  costruzione in ogni run sequenziale).
- Criterio di esclusione basato su cosmologia NaN: costruito su un artefatto
  (1800 mock su 2000 sono NaN). Ritirato.
- Correlazioni presentate come se fossero su 2000 punti: erano su 200.
- `violazioni_monotonia_frac` e `fuori_maschera_spearman` in v2h: metriche prive
  di significato ai valori di N in gioco. Da ignorare nei report.

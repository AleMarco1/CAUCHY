# Paper 2 — Item 1.2b e 1.2c: w̄ misurato, *d*_med identificato, esclusioni dichiarate
### 26 agosto 2026

> **Cancelli.** `data_side` fiduciale riprodotto a **2.9 × 10⁻⁹** (NGC) e **2.2 × 10⁻⁹** (SGC) su
> cinque quantità congelate, `n_valid_voxels` e `N_data` esatti all'unità. Undici geometrie per
> emisfero.

---

## 1. La provenienza del limite, trovata

Il blocco di archeologia ha localizzato l'unica definizione esistente, in
`src/paper2_v1_reference.json:127-128`:

```json
"practical_limit_NGC": 0.333,
"practical_rule": "sigma_px <~ d_med/9",
```

**Il nome della chiave è la risposta.** `practical_limit_NGC` dichiara da solo che 0.333 è tarato su
NGC. La tabella di triage lo aveva trasferito a SGC senza autorizzazione, ed è da lì che veniva
l'allarme di ieri sul fiduciale SGC.

Nessuna formula per *d*_med esiste nel sorgente: `practical_rule` è una nota, non un calcolo.

---

## 2. *d*_med identificato, per coincidenza doppia

Il blocco C misura la scala di campionamento su tutte le geometrie. Al fiduciale:

| | mediana distanza al 1º vicino | in h⁻¹Mpc |
|---|---|---|
| NGC | **0.33126 voxel** | 5.17 |
| SGC | **0.37980 voxel** | 5.65 |

**Prima coincidenza:** 0.33126 contro il congelato 0.333, scarto **0.5%**.

**Seconda coincidenza, indipendente:** il margine SGC che ne discende è **+11.5%**, contro il **+11.4%**
che avevo stimato ieri per via del tutto diversa, scalando *d*_med ∝ occupazione^(−1/3) dal rapporto
0.707 / 0.479 galassie per voxel.

Due strade indipendenti che convergono sullo stesso numero. L'identificazione è:

> **d_med = mediana della distanza al primo vicino fra le galassie, in unità di griglia.**
> Il criterio operativo è **σ_px ≤ *d*_med**, cioè: *il lisciamento non deve scendere sotto la scala
> di campionamento del tracciante.* In unità fisiche: *R* = 5.00 h⁻¹Mpc contro *d*_med(NGC) = 5.17.

**Il "/9" non è riproducibile e va ritirato.** Nessuna quantità misurata sulla nuvola vale 9 × 0.333 =
3.0 voxel: la spaziatura media è 1.12 voxel e il cinquantesimo vicino arriva a 2.19. Nel manoscritto
va scritto il criterio, non la formula ereditata.

---

## 3. w̄ misurato: il criterio non esclude nulla, ma nasconde una scalinata

Tutti e 22 i punti superano w̄ ≥ 0.99, il minimo essendo SGC C4 a 0.99524. **Il criterio del Paper 1,
applicato alla media, non esclude nessuna geometria.**

Ma la media nasconde ciò che conta:

| | | *k* = 0 | *k* = 1 | *k* = 2 | *k* = 3 |
|---|---|---|---|---|---|
| **NGC** | voxel | 307 805 | 260 100 | 213 726 | 171 112 |
| | w̄ | 0.997987 | 0.999991 | 1.000000 | 1.000000 |
| | *w*_min | 0.96289 | 0.99972 | 1.00000 | 1.00000 |
| | frac < 0.99 | **0.0780** | 0.0000 | 0.0000 | 0.0000 |
| **SGC** | voxel | 172 225 | 141 569 | 112 386 | 86 328 |
| | w̄ | 0.996417 | 0.999976 | 1.000000 | 1.000000 |
| | *w*_min | 0.94315 | 0.99933 | 1.00000 | 1.00000 |
| | frac < 0.99 | **0.1780** | 0.0000 | 0.0000 | 0.0000 |

A *k* = 0 il **17.8% dei voxel SGC** sta sotto soglia mentre la media segna 0.9964. E attraverso la
griglia AP quella frazione **non varia con continuità**.

### La scalinata, e dove sono i gradini

*w* di un voxel dipende da quanti vicini gli mancano. Con kernel gaussiano discreto, il peso perso
per un vicino di faccia è *w*₁(σ_px); la soglia 0.99 viene superata quando *n* vicini mancanti danno
*n*·*w*₁ > 0.01. Quindi il numero di vicini necessari cambia a gradini:

| gradino | σ_px | sotto → sopra |
|---|---|---|
| 2 → 1 vicino | **0.33023** | ne basta uno |
| 3 → 2 vicini | **≈ 0.3075** | ne bastano due |

La griglia AP li attraversa entrambi:

- **NGC**: frac < 0.99 vale 0.034 a C1 (σ = 0.30493), 0.077–0.078 per nove punti, **0.152 a C4**
  (σ = 0.33165). Due gradini dentro la griglia.
- **SGC**: 0.091 a A3 e C1, 0.168–0.179 per gli altri nove. **9 punti su 11 sopra il gradino
  principale.**

**È lo stesso rischio del gradino di tiling**: una discontinuità della costruzione che, se non
rilevata, verrebbe letta come risposta AP. Qui però la neutralizzazione è gratuita.

### La conseguenza operativa

> **La griglia AP va eseguita a erosione *k* = 1 come primaria.** A quel livello frac < 0.99 = 0 e
> *w*_min ≥ 0.99933 in **tutti** i punti di **entrambi** gli emisferi: la scalinata sparisce per
> costruzione.

Costo: −15.5% di voxel in NGC, −17.8% in SGC. Uniforme attraverso la griglia, quindi innocuo per una
misura **differenziale**, che è ciò che 3.4 misura. *k* = 0 va comunque riportato per l'aggancio ai
numeri v1.

---

## 4. Item 1.2c — la regola di esclusione, dichiarata

**Adottata:** σ_px ≤ *d*_med, con *d*_med = mediana della distanza al primo vicino in unità di
griglia, **ricalcolata per regione e per geometria**. Più w̄ ≥ 0.99 come secondo criterio.

**Respinta:** la lettura «regola di griglia» σ_px ≤ 1/3 uguale ovunque. Escluderebbe 9 punti SGC su
11 **compreso il fiduciale**, cioè un risultato già pubblicato in v1. Una regola che esclude il
proprio punto di riferimento è sbagliata, non severa.

### Verdetto

| | | esclusi | margine minimo |
|---|---|---|---|
| **NGC** | 11 punti | **C4** (Ω_m = 0.35, *w*₀ = −0.8), margine **−0.2%** | A1 a +0.5% |
| **SGC** | 11 punti | **nessuno** | C4 a +8.4% |

**Un solo punto escluso sull'intera griglia, ed è marginale.** −0.2% su un criterio scritto con «≲»
non è una violazione netta. Va trattato così:

- **primaria:** griglia senza NGC C4, come da regola dichiarata;
- **robustezza:** run con C4 incluso, riportato separatamente. Se sposta il risultato, è il criterio
  a essere in discussione, non il dato.

### Una perdita da dichiarare nel manoscritto

C4 è **uno dei due angoli che portano il canale oltre la famiglia (α_iso, *F*_AP)**: 0.047 voxel,
il 13.1% dell'ampiezza. L'altro, C1, sopravvive con +8.1% di margine e porta 0.082 voxel (14.5%).

Il terzo canale resta quindi **misurabile ma su un solo angolo in NGC**, e su entrambi in SGC dove
nessun punto è escluso. Il test di completezza di 1.3b va riformulato di conseguenza: la predizione
A+B → C si verifica su C1, C2, C3 in NGC e su tutti e quattro in SGC.

---

## 5. Da aggiornare

1. **`paper2_v1_reference.json`** — la chiave `practical_rule` va corretta da `"sigma_px <~ d_med/9"`
   a `"sigma_px <~ d_med, d_med = median 1-NN separation in grid units"`, e affiancata da
   `practical_limit_SGC: 0.3798`. *(Il file è nel tier `records`: il digest cambierà, va rifatto il
   freeze e annotato.)*
2. **`paper2_item12a_apgrid.py`** — `DMED_OVER_9 = 0.333` è una costante globale usata per
   `margin_vs_dmed9`: va sostituita col valore per regione, o rimossa in favore del calcolo di 1.2b.
3. **Checklist 1.2b/1.2c** — spuntabili, con i numeri qui sopra.
4. **Checklist 3.1 e 3.6** — aggiungere: *erosione k = 1 come livello primario per la griglia AP*.
5. **Practice §6.2 di M26, voce 1** — precisare: w̄ **e la frazione di voxel sotto soglia**, perché la
   media da sola non intercetta la scalinata.
6. **Figura F3** — mostrare frac < 0.99 accanto a w̄, con i due gradini tracciati: è la figura che
   rende visibile il problema.

---

## 6. Un difetto dello script, corretto

Nei log si vede che `set_geometry` echeggia il box del punto **precedente**: `data_side` riscrive
`box_min`/`box_size` nello stato globale del modulo, e alla fine del run quello stato resta quello
dell'ultima geometria — C4. Ripristinare `dc_tab` non basta.

Lo script ora chiude con una chiamata a `data_side` al fiduciale e **verifica** che il box torni al
valore congelato. Chi lavora dopo, nella stessa sessione, non eredita più una griglia sbagliata.

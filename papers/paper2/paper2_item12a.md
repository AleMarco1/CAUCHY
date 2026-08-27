# Paper 2 — Item 1.2a: tabella AP col box effettivo
### 25 agosto 2026 — metà cosmologica chiusa, metà geometrica pronta per la workstation

> **Cancello.** 12/12 valori di α_iso della tabella congelata riprodotti entro 2 × 10⁻⁴ da
> un'implementazione indipendente (integrazione trapezoidale di *D*_C su 90 001 nodi,
> *c*/*H*₀ = 2997.92458). Residui entro 0.03 h⁻¹Mpc, compatibili con la precisione di
> quadratura. Solo dopo questo il resto del documento.

---

## 1. Cosa è chiuso adesso, senza toccare i dati

Le colonne cosmologiche non dipendono dal catalogo: α_iso, residuo anisotropo, *F*_AP, monotonia.
Sono definitive.

| Ω_m | *w*₀ | α_iso | res. (h⁻¹Mpc) | *F* = α_∥/α_⊥ | *F* = α_⊥/α_∥ | monotona |
|---|---|---|---|---|---|---|
| 0.25 | −1.2 | 1.04052 | **11.46** | 1.0147 – **1.0405** | **0.9611** – 0.9856 | ✓ |
| 0.25 | −1.0 | 1.01496 | 5.08 | 1.0052 – 1.0201 | 0.9803 – 0.9949 | ✓ |
| 0.25 | −0.8 | 0.98918 | 1.65 | 0.9938 – 0.9965 | 1.0035 – 1.0062 | ✓ |
| 0.28 | −1.2 | 1.03201 | 8.45 | 1.0118 – 1.0292 | 0.9717 – 0.9883 | ✓ |
| 0.28 | −1.0 | 1.00819 | 2.74 | 1.0029 – 1.0109 | 0.9892 – 0.9972 | ✓ |
| 0.28 | −0.8 | 0.98404 | 3.34 | 0.9890 – 0.9937 | 1.0064 – 1.0112 | ✓ |
| 0.3175 | −1.2 | 1.02177 | 4.97 | 1.0083 – 1.0160 | 0.9842 – 0.9917 | ✓ |
| **0.3175** | **−1.0** | **1.00000** | **0.00** | **1.0000** | **1.0000** | ✓ |
| 0.3175 | −0.8 | 0.97777 | 5.38 | 0.9809 – 0.9914 | 1.0086 – 1.0195 | ✓ |
| 0.35 | −1.2 | 1.01323 | 2.17 | 1.0053 – 1.0076 | 0.9924 – 0.9947 | ✓ |
| 0.35 | −1.0 | 0.99312 | 2.23 | 0.9911 – 0.9976 | 1.0024 – 1.0090 | ✓ |
| 0.35 | −0.8 | 0.97247 | 7.07 | **0.9739** – 0.9895 | 1.0106 – **1.0268** | ✓ |

**Il cancello 2.4 è chiuso come sottoprodotto.** *f*(*r*) è strettamente crescente su
*z* ∈ [0.1, 0.4] in 12/12 punti. Costo: zero, è dentro `cosmo_row()`. Va spuntato nel checklist.

---

## 2. Tre discrepanze rispetto alla tabella congelata

### 2.1 La convenzione di *F*_AP non è quella standard — ma è coerente

La consegna riporta *"F_AP locale sull'intera griglia: 0.974 – 1.041"*. Quella escursione è
**esattamente** l'intervallo di α_∥/α_⊥ (calcolato: 0.9739 – 1.0405), cioè il **reciproco** della
convenzione consueta in letteratura, dove *F*_AP(*z*) = *D*_M(*z*)*H*(*z*)/*c* e quindi
*F*/*F*^fid = α_⊥/α_∥ = **0.9611 – 1.0268**.

Non è un errore: è una convenzione, e le due sono reciproche. Ma:

- **`make_dc_tab_ap(alpha_iso=, F_ap=, z_pivot=)` implementa una delle due**, e l'item 1.3 costruirà
  la linea *F*_AP pura passando quel parametro. Se la linea viene campionata con la convenzione
  sbagliata, i punti finiscono dalla parte opposta del fiduciale — non catastrofico su una griglia
  quasi simmetrica, ma la derivata ∂*D*/∂*F*_AP cambia segno.
- **Verifica di dieci minuti, da fare prima di 1.3:** chiamare `make_dc_tab_ap(alpha_iso=1.0,
  F_ap=1.03, z_pivot=...)`, ricavare *D*_C(*z*), calcolare α_⊥ = *D*_C/*D*_C^fid e
  α_∥ = (d*D*_C/d*z*)^fid/(d*D*_C/d*z*), e vedere quale rapporto vale 1.03.
- **Nel manoscritto la convenzione va dichiarata esplicitamente**, con la formula, non solo il nome.

### 2.2 La colonna "in voxel" e la colonna σ_px usavano due Δ*x* diversi

Nella tabella congelata:

- la colonna **σ_px = 0.3204/α_iso** assume Δ*x* ∝ α_iso;
- la colonna **"in voxel"** riproduce invece residuo/Δ*x*_fid, con Δ*x* fisso a 15.6044.

Verifica: (0.25, −1.2) → 11.46/15.6044 = **0.734** ≈ 0.73 riportato; con Δ*x* scalato darebbe 0.706.
(0.35, −0.8) → 7.07/15.6044 = **0.453** ≈ 0.45 riportato; con Δ*x* scalato 0.466.

Le due colonne sono quindi internamente incoerenti. L'item 1.2a esiste proprio per superare
entrambe le approssimazioni con Δ*x* effettivo, ma finché non gira la metà geometrica:

| | Δ*x* = Δ*x*_fid (tabella congelata) | Δ*x* = α_iso·Δ*x*_fid | **da usare** |
|---|---|---|---|
| residuo max NGC | 0.734 | 0.706 | Δ*x* effettivo |
| residuo max SGC | 0.770 | 0.740 | Δ*x* effettivo |

**Il numero da citare nel manoscritto è il massimo sui due emisferi, non solo NGC.** Il residuo
anisotropo in voxel è ~4.9% più grande in SGC perché Δ*x* è più piccolo (14.88 contro 15.60). Con
0.740 voxel contro l'artefatto di padding di 0.0131 voxel il rapporto resta **56×**, quindi la frase
scritta ieri per §2 regge senza modifiche.

### 2.3 α_box ≠ α_iso, e lo scarto è esattamente la Prop. 2′

Il rapporto dei lati del cubo, α_box = *L*(punto)/*L*(fid), **non** coincide con α_iso: differisce di
2 × 10⁻⁴ per il padding additivo. Il selftest, che lavora su un footprint sintetico e non sa nulla
dell'algebra di ieri, restituisce ad α = 1.0406 uno scarto **−2.17 × 10⁻⁴**, contro le
**−2.166 × 10⁻⁴** della forma chiusa *a*(α) = α(*E*+2*p*)/(α*E*+2*p*). Due vie indipendenti, tre
cifre significative.

Conseguenza pratica: **α_iso e α_box vanno riportati come colonne separate**, e la parametrizzazione
dell'item 1.3 deve dichiarare quale delle due controlla. Se la linea "α_iso pura" viene costruita
imponendo α_box, il test di chiusura non darà zero esatto ma il residuo di padding.

---

## 3. Cosa manca, e cosa serve per averlo

La metà geometrica richiede il catalogo random della regione. Lo script è pronto e validato.

```powershell
# validazione della meccanica, secondi, non richiede dati
python src\paper2_item12a_apgrid.py --selftest

# metà cosmologica, riproducibile a comando
python src\paper2_item12a_apgrid.py --cosmo-only --out results\paper2\item12a_cosmo.jsonl

# metà geometrica
python src\paper2_item12a_apgrid.py --region NGC --randoms <path_random_NGC> `
    --ra-col RA --dec-col DEC --z-col Z --out results\paper2\item12a_NGC.jsonl
python src\paper2_item12a_apgrid.py --region SGC --randoms <path_random_SGC> `
    --ra-col RA --dec-col DEC --z-col Z --out results\paper2\item12a_SGC.jsonl
```

Lo script produce, per ogni punto: estensioni per asse, **asse dominante**, *L*, Δ*x*, α_box,
σ_px effettivo, residuo in voxel col Δ*x* giusto, margine sul limite, e tre flag —
`CAMBIO-ASSE`, `ESCLUSO-sigma_px`, `a_box!=a_iso`. Output JSONL append-only, scrittura atomica con
`fsync`, ripartibile per firma di configurazione.

### Predizioni dichiarate prima del run

Registrate ora, secondo il protocollo:

1. **Cancello geometrico.** Al punto fiduciale il box ricomputato deve dare *L* = 1997.36 (NGC) e
   1904.64 (SGC) entro 0.05 h⁻¹Mpc. Se fallisce, il box **non** è derivato dai random con la regola
   `max_k(estensione) + 2p`, e lo script si ferma con codice 3 invece di produrre numeri.
2. **Asse dominante.** Predico **nessun cambio di asse** sulla griglia (Ω_m, *w*₀): la deformazione
   radiale è ≤ 5%, e il margine dell'asse dominante su un footprint di quella forma è tipicamente
   dell'ordine delle decine di punti percentuali. Se il margine risultasse invece **sotto il 5%**, il
   cambio di asse diventa possibile sulla linea *F*_AP pura di 1.3 e va trattato come il gradino di
   tiling: artefatto di costruzione, non derivata.
3. **α_box.** |α_box − α_iso| ≈ 2 × 10⁻⁴ agli angoli, con il segno opposto a (α−1).
4. **σ_px effettivo.** Vicino a 0.3204/α_iso entro ~2 × 10⁻⁴ relativo, per lo stesso motivo. Non
   abbastanza da spostare il verdetto di 1.2c su nessun punto — l'angolo (0.35, −0.8) resterà
   all'1.1% di margine, non passerà all'improvviso.

### Un limite dichiarato

Il limite pratico *d*_med/9 = 0.333 è trattato come costante, ma *d*_med in unità di griglia **non**
lo è sotto deformazione anisotropa (sotto dilatazione isotropa sì, per la Prop. 2). Ricalcolarlo per
punto richiede il catalogo galassie e un kd-tree; è lavoro dell'item **1.2b**, che comunque deve
girare `mask_erosion` per w̄. Fino ad allora il margine in tabella è approssimato.

---

## 4. Ricaduta sull'item 1.3

Numeri utili al design della griglia definitiva, già disponibili:

- L'escursione fisica di *F*_AP sull'intera griglia (Ω_m, *w*₀) è **0.9611 – 1.0268** nella
  convenzione α_⊥/α_∥, cioè circa **±2.7%**. La linea *F*_AP pura deve coprire almeno questo
  intervallo per essere rilevante, ancorata ai due angoli che lo realizzano: (0.25, −1.2) e
  (0.35, −0.8).
- Campionamento proposto, cinque punti: *F*_AP ∈ {0.961, 0.980, 1.000, 1.013, 1.027}, ad α_iso = 1.
- La linea α_iso pura può essere corta — tre punti, {0.9725, 1.0000, 1.0406} — perché è un test di
  chiusura ad attesa nota, non una misura.
- I quattro angoli di controllo restano (0.25, −1.2), (0.25, −0.8), (0.35, −1.2), (0.35, −0.8).

Totale: 3 + 5 + 4 − 1 (fiduciale in comune) = **11 punti**, ma tre della linea α_iso costano quanto
un cancello. Il carico reale è 5 + 4 = 9 geometrie complete.

---

## 5. Da aggiornare negli altri documenti

1. **Consegna §5.4 e checklist 1.2** — la riga "*F*_AP locale sull'intera griglia: 0.974–1.041" va
   qualificata con la convenzione: *"F = α_∥/α_⊥; nella convenzione standard D_M H/c l'escursione è
   0.961–1.027"*.
2. **Colonna "in voxel"** — dichiarare quale Δ*x*; sostituire con Δ*x* effettivo appena gira la metà
   geometrica; citare il massimo sui due emisferi (0.740, non 0.73).
3. **Checklist 2.4** — spuntabile ora: 12/12 monotoni.
4. **Checklist 1.2a** — aggiungere la colonna asse dominante e le tre flag.
5. **Item 1.3** — aggiungere il controllo di convenzione su `make_dc_tab_ap` come precondizione.

---

## Prossimo

**Item 1.2b** (w̄ esatto per punto con `mask_erosion`) dipende dai run geometrici; **1.5a** (tiling)
è indipendente e può girare in parallelo. Se preferisci non aspettare la workstation, l'item **1.3**
è formulabile subito nella parte di design, con la sola precondizione del controllo di convenzione
su `make_dc_tab_ap`.

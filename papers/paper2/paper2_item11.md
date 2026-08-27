# Paper 2 — Item 1.1: Proposizione 2, enunciato, dimostrazione e punti di rottura
### 25 agosto 2026 — chiude 1.1a, 1.1b, 1.1c

> **Cancello di sessione.** Riprodotto prima di scrivere: peso centrale del kernel gaussiano discreto
> a σ_px = 0.3204 → **95.54%** in 3D, contro il 95.54% del Paper 1 §2. Punto fisso della dilatazione
> residua verificato a *u* = 63.99999999999 = *N*/2.

---

## 0. Notazione

Catalogo galassie {**r**_i} e random {**R**_j} in coordinate comoventi, ottenuti da (RA, Dec, *z*)
via **r** = *D*_C(*z*)·**n̂** con una fiducia assegnata. La pipeline è la composizione

| | passo | dipende da |
|---|---|---|
| P1 | box: *o*_k = min_j *R*_jk − *p*; *E* = max_k (max_j *R*_jk − min_j *R*_jk); *L* = *E* + 2*p*; Δ*x* = *L*/*N* | posizioni fisiche |
| P2 | coordinate di griglia *u*_ik = (*r*_ik − *o*_k)/Δ*x* | P1 |
| P3 | assegnazione CIC: *F*(**c**) = Σ_i *w*_i *W*(**u**_i − **c**) | **solo** *u* |
| P4 | maschera dai random, soglia sulla densità CIC media | **solo** *u* |
| P5 | δ = *F*/*F̄* − 1; α_norm = Σ*w*_g/Σ*w*_r | **solo** *u* |
| P6 | ν = *G*_σpx ∗ δ, σ_px in unità di griglia | **solo** *u* |
| P7 | filtrazione di supralivello su complesso cubico, PD, *N*_H1, β₁(ν) | **solo** *u* |

*N* = 128, *p* = 5 h⁻¹Mpc nell'implementazione. **Il punto strutturale è che P3–P7 non contengono
nessuna lunghezza fisica.** Tutto ciò che porta unità h⁻¹Mpc sta in P1.

---

## 1.1a — Enunciato e dimostrazione

### Lemma A (equivarianza della griglia)

> Sia *T* una trasformazione di ℝ³ applicata a galassie **e** random. Se la regola P1 è tale che,
> sotto *T*, l'origine e il passo si trasformano in *o* → *T*(*o*) e Δ*x* → λΔ*x* con
>
> &nbsp;&nbsp;&nbsp;&nbsp;(*T*(**r**) − *T*(*o*))/λΔ*x* = (**r** − *o*)/Δ*x*&nbsp;&nbsp;∀**r**,
>
> allora le coordinate di griglia {**u**_i} sono **puntualmente identiche**. Poiché P3–P7 sono
> funzioni delle sole {**u**_i}, il campo *F*, la maschera, δ, α_norm, ν, la filtrazione e l'**intero
> diagramma di persistenza** sono identici cella per cella.

*Dimostrazione.* Immediata per composizione: **u** è l'unico canale attraverso cui P1 comunica con
P3. ∎

### Proposizione 2 (forma esatta)

> Sia il cubo di embedding costruito dal bounding box del catalogo random su griglia *N*³ con padding
> **nullo o moltiplicativo**, e sia σ_px fissato in **unità di griglia**. Allora, sotto dilatazione
> isotropa **r** → α**r** con α > 0 applicata a galassie e random, il diagramma di persistenza è
> **esattamente invariante**, e con esso *N*_H1, β₁(ν), la maschera e α_norm.

*Dimostrazione.* L'estensione è una differenza di coordinate, dunque *E* → α*E* esattamente. Con
padding moltiplicativo *p* → α*p* (o *p* = 0) si ha *L* → α*L*, Δ*x* → αΔ*x*, *o* → α*o*. Quindi

&nbsp;&nbsp;&nbsp;&nbsp;(α*r*_ik − α*o*_k)/(αΔ*x*) = (*r*_ik − *o*_k)/Δ*x*.

Le ipotesi del Lemma A valgono con λ = α. ∎

**Tre righe, come chiedeva 1.1a.** Vale la pena notare esplicitamente che la dimostrazione **non usa
nulla di topologico**: non dipende dallo schema di assegnazione (NGP, CIC, TSC), né dal kernel, né
dal grado di omologia, né dal criterio di persistenza. È una proposizione sulla **parametrizzazione**,
non sulla statistica. Questo è anche il modo giusto di distinguerla dalla Proposizione 1 (§1.1c).

### Corollario 1 — La componente isotropa dell'AP è una convenzione di griglia

L'unica quantità di P3–P7 che può portare informazione sulla dilatazione è σ_px = *R*/Δ*x*, e solo
perché *R* è dichiarato in h⁻¹Mpc. Con σ_px fissato in unità di griglia la risposta AP isotropa è
**identicamente nulla**, non "piccola". La scelta fra le due convenzioni non è neutra sotto AP: è la
terza "practice" da aggiungere a §6.2 di M26.

### Corollario 2 — L'evidenza empirica è già in mano

NGC e SGC hanno Δ*x* = 15.60 e 14.88 h⁻¹Mpc, una differenza del **4.6%**, più grande dell'intera
escursione α_iso della griglia (0.9725–1.0406, cioè 6.8% estremo-estremo ma ≤ 4.1% dal fiduciale). I
due emisferi danno deficit 20.3% e 19.1%. La dilatazione isotropa è già stata testata di fatto, a
costo zero.

### Corollario 3 — La linea α_iso pura è un test di chiusura, non una misura

Ogni punto della griglia con *F*_AP = 1 deve restituire scarto nullo (a meno del residuo di §1.1a′).
Va eseguita e riportata come verifica, e **non** interpretata come derivata ∂*N*_H1/∂fiducia.

---

## 1.1a′ — Proposizione 2 emendata: l'implementazione usa padding additivo

L'implementazione fissa *p* = 5 h⁻¹Mpc indipendentemente da α. Il box scala allora come α*E* + 2*p*
invece di α(*E* + 2*p*), e l'ipotesi del Lemma A cade. Il residuo, però, ha forma chiusa.

### Proposizione 2′

> Con padding additivo *p* costante, la mappa dalle coordinate di griglia a α = 1 a quelle a α
> generico è l'**affinità**
>
> &nbsp;&nbsp;&nbsp;&nbsp;*u*_k(α) = *a*(α)·*u*_k(1) + *b*(α),&nbsp;&nbsp;
> *a*(α) = α(*E*+2*p*)/(α*E*+2*p*),&nbsp;&nbsp; *b*(α) = *N p*(1−α)/(α*E*+2*p*),
>
> identica in tutti e tre gli assi, con **punto fisso *u*\* = *N*/2** (il centro geometrico del cubo).
> È dunque una **dilatazione isotropa residua** di fattore *a*(α) = 1 + 2*p*(1−α)/(α*E*+2*p*) attorno
> al centro della griglia. Lo spostamento massimo di una galassia rispetto alla griglia è
>
> &nbsp;&nbsp;&nbsp;&nbsp;max |Δ*u*| = (*N*/2)·|*a*−1| = *N p* |1−α| / (α*E* + 2*p*).

*Dimostrazione.* Posto *s*_k = *r*_k − min_k, si ha *u*_k(α) = (α*s*_k + *p*)*N*/(α*E* + 2*p*),
affine in *s*_k e quindi in *u*_k(1) = (*s*_k + *p*)*N*/(*E* + 2*p*). Sostituendo si ottengono *a* e
*b*; il punto fisso *b*/(1−*a*) si semplifica in *N*/2 perché 1 − *a* = 2*p*(1−α)/(α*E*+2*p*). ∎

### Numeri

Con *N* = 128, *p* = 5, *L*_NGC = 1997.36 e *L*_SGC = 1904.64 h⁻¹Mpc:

| α_iso | dilatazione residua *a*−1 | max |Δ*u*| NGC | max |Δ*u*| SGC | stima circolante 2*p*(1−α)/Δ*x* |
|---|---|---|---|---|
| 0.9725 | −1.42 × 10⁻⁴ | 0.0091 | 0.0095 | 0.0176 |
| 0.9892 | −5.47 × 10⁻⁵ | 0.0035 | 0.0037 | 0.0069 |
| **1.0000** | **0** | **0** | **0** | **0** |
| 1.0132 | +6.52 × 10⁻⁵ | 0.0042 | 0.0044 | 0.0085 |
| 1.0320 | +1.55 × 10⁻⁴ | 0.0099 | 0.0104 | 0.0205 |
| **1.0406** | **+1.95 × 10⁻⁴** | **0.0125** | **0.0131** | **0.0260** |

**Correzione da portare nel manoscritto.** La stima 2*p*(1−α)/*L* che circola nella consegna è il
**diametro** dell'escursione, non lo spostamento massimo: è conservativa di un fattore **2 esatto**,
perché ignora che il punto fisso è al centro del cubo. La frase corretta è

> *"invariante a 1.4 × 10⁻² voxel sull'intera griglia AP e in entrambi gli emisferi"*

contro un residuo anisotropo fisico di **0.73 voxel**. Il rapporto segnale/artefatto passa da 29× a
**56×**.

### Tre proprietà del residuo, tutte favorevoli

1. **È isotropo.** Essendo una dilatazione affine attorno al centro, non può produrre né imitare una
   firma *F*_AP. Contamina solo la linea α_iso pura, che è già un test ad attesa nulla.
2. **È continuo.** L'assegnazione CIC è lineare a tratti nella posizione: uno spostamento sub-voxel
   perturba *F* con continuità, senza salti. Nessuna galassia "cade" in un'altra cella in senso
   discreto; cambia solo la ripartizione dei pesi fra le 8 celle di supporto, e il peso trasferito
   attraverso un confine tende a zero per continuità.
3. **Non rompe i pareggi esatti.** Le celle esattamente vuote restano esattamente vuote (δ = −1
   esatto) sotto qualunque ridistribuzione continua di peso. *Ipotesi da verificare a costo zero
   dentro il cancello 2.2a:* se i 4272 gruppi di celle appaiate di M26 R1 §4.1 sono in maggioranza
   celle vuote, il residuo non li tocca, e la rottura di 3 generatori (0.011%) misurata lì non si
   somma qui.

### Predizione dichiarata per i cancelli 2.2a / 2.2b

Registrata **prima** dell'esecuzione, secondo il protocollo del cancello:

- **2.2b** (padding riscalato, `pad = 5.0 * alpha_iso`): scarto **esattamente 0**. Qualunque valore
  diverso da zero falsifica la Proposizione 2 come applicata alla pipeline, non la proposizione.
- **2.2a** (padding additivo, α = 1.05): scarto |Δ*N*_H1| **≤ 5 generatori**, cioè ≤ 0.018% di
  28 256. Motivazione: perturbazione del campo di ordine 1.5 × 10⁻² voxel × gradiente di cella, con
  CIC continua e pareggi esatti conservati; *N*_H1 cambia solo dove due valori di cella si
  incrociano. Uno scarto > 5 generatori significa che **qualcos'altro** nella pipeline non è
  equivariante, e va cercato prima di proseguire.
- Nota di taratura: α = 1.05 del cancello è **fuori** dall'intervallo fisico della griglia
  (|1−α| ≤ 0.0406). Il cancello è quindi deliberatamente conservativo, ma il numero da citare nel
  manoscritto per il canale isotropo va valutato agli α della griglia, non a 1.05.

### Predizione dichiarata per il cancello 2.3

Con *R* fisso a 5 h⁻¹Mpc e α = 1.05, σ_px = 0.3051 invece di 0.3204. Il peso del voxel centrale nel
kernel gaussiano discreto passa da **95.54% a 97.26%** in 3D: meno smoothing.

| σ_px | contesto | peso centrale 3D |
|---|---|---|
| 0.3295 | estremo griglia α = 0.9725 | 94.24% |
| **0.3204** | **fiduciale** | **95.54%** |
| 0.3079 | estremo griglia α = 1.0406 | 96.99% |
| 0.3051 | cancello 2.3, α = 1.05 | 97.26% |
| 0.333 | limite pratico *d*_med/9 | 93.67% |

**Predizione: Δ*N*_H1 > 0**, cioè *N*_H1 aumenta. Con occupazione 0.71 galassie per voxel il campo è
dominato dallo shot noise alla scala di cella, e meno smoothing trattiene più struttura a piccola
scala, dunque più anelli. Se il segno risulta negativo, va registrato come predizione fallita nel
record — non riscritto a posteriori.

---

## 1.1b — Dove la proposizione si rompe

Inventario esplicito. La colonna "misura" è la quantità che chiude il punto; la colonna "stato" dice
se il numero esiste già.

| | rottura | perché | misura | valore | stato |
|---|---|---|---|---|---|
| **(i)** | **Tassellazione della scatola periodica** | il cubo scala con α_iso, la scatola Quijote resta a 1000 h⁻¹Mpc | frazione indipendente e molteplicità per punto, mapping `x mod L_box` | 0.76 → **0.70** (misurata) → 0.62; molteplicità media **1.44**, max 5; inflazione della dispersione **< 12% al 95%** | M26 R1 §5.6; da estendere a ogni punto in **1.5a** |
| **(i-bis)** | **Gradino discreto di tiling** | a α_iso ≳ 1.001 il lato supera 2000 h⁻¹Mpc e cambia il numero di offset interi intersecanti | numero di repliche intersecanti per punto | non ancora misurato | **1.5a**; neutralizzazione in 3.2b |
| **(ii)** | **Inversione *r* → *z*_cosmo nel carving** | selezione *n*(*z*) e RSD sono definite in *z*, non in unità di griglia: cambiando fiducia cambia **quali** galassie entrano | numero di galassie che cambiano stato di selezione, per punto | non ancora misurato | **3.2**, registrazione obbligatoria |
| **(ii-bis)** | **Finestra radiale del pre-filtro** | `carve_cutsky:444` pre-filtra con margine ±50 h⁻¹Mpc attorno a `D_C_ZMIN/ZMAX`; il taglio vero è a riga 453 | spostamento massimo di *D*_C per punto | morde solo a (Ω_m, *w*₀) = (0.25, −1.2): **+55.26 h⁻¹Mpc** | risolto: `set_geometry()` imposta `D_C_ZMIN/ZMAX` coerentemente |
| **(iii)** | **Padding additivo (ex "arrotondamenti CIC al bordo")** | *p* = 5 h⁻¹Mpc non scala con α | max |Δ*u*| = *Np*|1−α|/(α*E*+2*p*) | **≤ 0.0131 voxel** su tutta la griglia, entrambi gli emisferi | **chiuso analiticamente qui**; verifica in 2.2a/b |
| **(iv)** | **Convenzione σ_px** | *R* dichiarato in h⁻¹Mpc, non in unità di griglia | scarto 2.3 − 2.2 | peso centrale 95.54% → 97.26% ad α = 1.05 | **2.3**; per definizione **è** l'intero canale isotropo |
| **(v)** | **Asse dominante del lato del cubo** | se *L* = max_k(estensione_k) + 2*p*, sotto *F*_AP ≠ 1 l'argmax può cambiare asse | quale asse fissa *L*, per punto | non ancora misurato — **voce nuova** | da aggiungere a **1.2a** |

### Due voci che **non** sono rotture, e vanno dette come tali

- **Regola della maschera.** Le due definizioni in circolazione differiscono di −3.27% nel conteggio
  dei voxel, cioè ~1.1 pp di deficit (18% della banda sistematica). È un'ambiguità di **convenzione**,
  non una rottura della Proposizione 2: sotto dilatazione esatta la maschera è invariante come tutto
  il resto, perché deriva anch'essa dalle sole coordinate di griglia. `build_mask(rule="v1_fullcube")`
  è la sola che riproduca v1, e va dichiarata una volta per tutte.
- **Invarianza monotona.** Nessuna trasformazione monotona del campo entra qui. È la Proposizione 1,
  ortogonale a questa (§1.1c).

### Osservazione sulla voce (v), da portare in 1.2a

La rottura (v) è **nuova rispetto alla consegna** e ha la stessa struttura del gradino di tiling: una
discontinuità nella costruzione che, se non rilevata, verrebbe letta come risposta AP. Sotto
dilatazione isotropa l'argmax è stabile per costruzione (tutti gli assi scalano di α), quindi il
problema non esiste sulla linea α_iso pura. Sotto *F*_AP la deformazione è radiale, e la direzione
radiale varia sul footprint: le tre estensioni cartesiane cambiano di quantità diverse. **1.2a deve
riportare, per ogni punto, l'asse che fissa il lato**, e segnalare ogni cambio. Costo: nullo, è già
dentro `derive_box()`.

---

## 1.1c — Posizionamento rispetto ai due antecedenti

Tre risultati, spesso confusi perché tutti e tre dicono "invariante":

| | risultato | oggetto dell'invarianza | dove |
|---|---|---|---|
| **Prop. 1** | invarianza monotona | l'**ordine** dei valori di cella: ogni *g* crescente lascia il PD invariato | Paper 1 §2.3 (formalizzata); M26 R1 §4.1 (enunciata e verificata in proprio: quantili normali, exp(3ν), ν³ → β₁^max invariato a 28 256; 4272 gruppi appaiati, la cui rottura sposta 3 generatori, 0.011%) |
| **Prop. 2** | invarianza per dilatazione | l'**identità delle celle**: quali galassie stanno in quale voxel | questo paper |
| **Prop. 2′** | quantificazione del residuo di implementazione | ≤ 1.4 × 10⁻² voxel | questo paper |

Le due proposizioni sono **strutturalmente diverse e componibili**. La Prop. 2 dice che i valori di
cella sono *identici*; la Prop. 1 dice che, anche se fossero rimappati in modo monotono, il diagramma
sarebbe lo stesso. La prima riguarda il dominio della funzione di campo, la seconda il codominio.
Nel testo vanno citate entrambe, in quest'ordine, con la formula: *la Prop. 2 chiude il canale
geometrico, la Prop. 1 chiude il canale di ampiezza; il deficit non vive in nessuno dei due.*

Il cancello 2.2 resta la verifica decisiva: la Prop. 2 è un teorema sulla pipeline **come
specificata**, e solo il cancello dice se la pipeline implementata la soddisfa.

---

## Testo pronto per il manoscritto (§2)

> **Proposition 2.** *Let the embedding cube be derived from the bounding box of the random catalogue
> on an N³ grid, with padding that is either zero or proportional to the box extent, and let the
> smoothing scale σ_px be fixed in grid units. Then the persistence diagram of the voxelized field —
> and hence N_H1, β₁(ν), the mask, and the normalization α = Σw_g/Σw_r — is exactly invariant under
> any isotropic dilation r → αr applied to galaxies and randoms alike.*
>
> *Proof.* Grid coordinates enter the pipeline only through u_i = (r_i − o)/Δx. The box extent is a
> difference of coordinates, so it scales exactly as α; with proportional padding, o → αo and
> Δx → αΔx, whence u_i is unchanged. Every subsequent step — mass assignment, mask construction,
> density contrast, smoothing, superlevel filtration — is a function of {u_i} alone. ∎
>
> The proof invokes no property of persistent homology: it concerns the parametrization, not the
> statistic, and holds for any mass-assignment scheme, any kernel specified in grid units, and any
> homological degree. It is therefore complementary to, and independent of, the monotone-invariance
> lemma of Paper 1 §2.3, which constrains the codomain of the field rather than its domain.
>
> Two consequences follow. First, the isotropic component of an Alcock–Paczyński rescaling is
> **degenerate with the grid convention**: it can enter N_H1 only through σ_px = R/Δx, that is, only
> because R is nominally quoted in h⁻¹Mpc. Second, only the curvature of the radial remapping — the
> anisotropic warp F_AP — carries physical content, so the fiducial-cosmology grid must be
> parametrized in (α_iso, F_AP) rather than in (Ω_m, w₀).
>
> Our implementation uses an additive padding of p = 5 h⁻¹Mpc, so the box scales as αE + 2p rather
> than α(E + 2p). The residual is an isotropic dilation about the grid centre by a factor
> a(α) = α(E + 2p)/(αE + 2p), displacing any galaxy by at most Np|1 − α|/(αE + 2p) grid units. Over
> the full AP grid and in both hemispheres this is **below 1.4 × 10⁻² voxel**, against a physical
> anisotropic residual of 0.73 voxel — a factor of 56. Proposition 2 therefore holds for the
> pipeline as implemented to within 1.4 × 10⁻² voxel, and exactly once the padding is rescaled.

---

## Da riportare negli altri documenti

1. **Consegna §5.1** — sostituire "≤ 0.025 voxel" con "≤ 1.4 × 10⁻² voxel", indicando che la stima
   precedente era il diametro dell'escursione e non lo spostamento massimo.
2. **Checklist 1.2a** — aggiungere: *riportare, per ogni punto, l'asse cartesiano che fissa il lato
   del cubo; segnalare ogni cambio di argmax attraverso la griglia*.
3. **Checklist 2.2a** — sostituire "scarto atteso ≤ 1 generatore" con la predizione dichiarata
   "≤ 5 generatori", con la motivazione di §1.1a′.
4. **Sottoprodotti** — la forma chiusa di Prop. 2′ (punto fisso al centro, fattore *a*) è materiale
   per la figura F4.
5. **Checklist 1.1b** — la voce (iii) passa da "arrotondamenti CIC al bordo del cubo" a "padding
   additivo", che è la causa reale; gli arrotondamenti CIC sono continui e non contribuiscono.

---

## Prossimo

**Item 1.2a.** Ricalcolo della tabella AP col bounding box effettivo dai random per ogni punto, più
la voce nuova sull'asse dominante. Serve `paper2_data_geometry.py` (`positions()`, `derive_box()`,
`data_side()`) su una tabella *D*_C(*z*) per punto, costruita con `make_dc_tab_ap`. Costo: minuti.
